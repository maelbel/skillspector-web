"""Run scans inside a Vercel Sandbox (an ephemeral Firecracker microVM), for hosted mode.

The target is fetched and analysed in the VM, never in the app: the app only uploads
sandbox_runner.py, starts it, and reads its event stream back. Each scan gets a fresh,
non-persistent VM, booted from a snapshot that already has skillspector installed (build one
with ``python -m app.sandbox_snapshot``), with outbound traffic limited to the code hosts a scan
can fetch from.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterable, Callable
from pathlib import Path
from typing import Any, Literal

from app import scan_logs
from app.core.config import Settings
from app.core.mode import Mode
from app.sandbox_runner import PREFIX

ExecutorKind = Literal["local", "sandbox"]

RUNNER_SOURCE = (Path(__file__).parent / "sandbox_runner.py").read_text()
RUNNER_PATH = "/vercel/sandbox/sandbox_runner.py"

# Where skillspector fetches targets from (see describeScanTarget in shared/utils/scan.ts),
# including the hosts GitHub and Hugging Face redirect downloads to. TLS only: the allow-list
# matches on SNI.
SCAN_HOSTS = (
    "github.com",
    "codeload.github.com",
    "raw.githubusercontent.com",
    "objects.githubusercontent.com",
    "gitlab.com",
    "bitbucket.org",
    "huggingface.co",
    "cdn-lfs.huggingface.co",
    "cdn-lfs-us-1.hf.co",
)

# Never reachable from a scan, whatever a target's DNS resolves to: private, loopback,
# link-local (including cloud metadata endpoints) and carrier-grade NAT ranges.
BLOCKED_SUBNETS = (
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "127.0.0.0/8",
    "169.254.0.0/16",
    "100.64.0.0/10",
)


def executor_kind(settings: Settings) -> ExecutorKind:
    """SKILLSPECTOR_WEB_SCAN_EXECUTOR when set, otherwise the mode's default."""
    if settings.scan_executor:
        return settings.scan_executor
    return "sandbox" if settings.mode is Mode.HOSTED else "local"


def scan_network_policy() -> Any:
    from vercel.sandbox import NetworkPolicy, NetworkPolicySubnets

    return NetworkPolicy.custom(
        allow={host: () for host in SCAN_HOSTS},
        subnets=NetworkPolicySubnets(deny=list(BLOCKED_SUBNETS)),
    )


class SandboxExecutor:
    def __init__(self, settings: Settings, create_sandbox: Callable[..., Any] | None = None) -> None:
        if not settings.sandbox_snapshot_id:
            raise ValueError("SKILLSPECTOR_WEB_SANDBOX_SNAPSHOT_ID is required to run scans in a sandbox")
        self._settings = settings
        if create_sandbox is None:
            from vercel.sandbox import create_sandbox
        self._create_sandbox = create_sandbox

    async def run(self, job_id: str, target: str, *, use_llm: bool) -> dict[str, Any]:
        if use_llm:
            # Provider keys will be brokered at the sandbox firewall (#46), never passed into the VM.
            raise RuntimeError("AI review can't run in the scan sandbox yet")

        from vercel.sandbox import SandboxError, SandboxResources, SnapshotSource

        settings = self._settings
        limit = settings.sandbox_timeout_seconds
        scan_logs.append(job_id, f"Starting scan of {target}")
        try:
            async with self._create_sandbox(
                source=SnapshotSource(snapshot_id=settings.sandbox_snapshot_id),
                resources=SandboxResources(vcpus=settings.sandbox_vcpus),
                # A little headroom over the scan itself for boot and upload.
                execution_time_limit=limit + 60,
                persistent=False,
                network_policy=scan_network_policy(),
                tags={"app": "skillspector-web", "scan": job_id},
            ) as box:
                await box.fs.write_text(RUNNER_PATH, RUNNER_SOURCE)
                process = await box.create_process("python3", [RUNNER_PATH, target], kill_after=limit)
                report, error = await self._consume(job_id, process.stdout)
                returncode = await process.wait()
        except SandboxError as exc:
            scan_logs.append(job_id, f"Scan failed: {exc}")
            raise RuntimeError(f"The scan sandbox failed: {exc}") from exc

        if report is not None and returncode == 0:
            scan_logs.append(job_id, "Scan complete")
            return report
        message = error or (
            f"The scan didn't finish within {limit:g} seconds"
            if returncode in (-9, 137)
            else f"The scan stopped unexpectedly (exit code {returncode})"
        )
        scan_logs.append(job_id, f"Scan failed: {message}")
        raise RuntimeError(message)

    async def _consume(self, job_id: str, lines: AsyncIterable[str] | None) -> tuple[dict[str, Any] | None, str | None]:
        """Relay the runner's events into the scan's log and progress as they arrive."""
        report: dict[str, Any] | None = None
        error: str | None = None
        if lines is None:
            return report, error
        async for raw in lines:
            if not raw.startswith(PREFIX):
                continue  # Anything else on stdout isn't ours.
            try:
                event = json.loads(raw[len(PREFIX) :])
            except json.JSONDecodeError:
                continue
            kind = event.get("event")
            if kind == "step":
                scan_logs.append(job_id, f"{event['node']} completed")
                scan_logs.increment_progress(job_id)
            elif kind == "log":
                scan_logs.append(job_id, event["line"])
            elif kind == "report":
                report = event["report"]
            elif kind == "error":
                error = event["message"]
            elif kind == "start":
                self._check_version(job_id, event.get("skillspector_version"))
        return report, error

    @staticmethod
    def _check_version(job_id: str, sandbox_version: str | None) -> None:
        from skillspector import __version__ as app_version

        if sandbox_version != app_version:
            scan_logs.append(
                job_id,
                f"WARNING The scan sandbox runs skillspector {sandbox_version}, the API {app_version}; "
                "rebuild the snapshot with python -m app.sandbox_snapshot",
            )
