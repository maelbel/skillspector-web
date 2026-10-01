"""Run one skillspector scan and report on stdout, one tagged JSON event per line.

This file is uploaded into a Vercel Sandbox and run there with
``python3 sandbox_runner.py <target> [--llm] [--baseline FILE] [--transitive-depth N
[--transitive-allow PREFIX]... [--transitive-deny PREFIX]...]`` (``--llm`` adds skillspector's AI
review; ``--baseline`` suppresses the findings a baseline accepts; ``--transitive-depth`` follows
the skill's external references and scans them too), so it must stay standalone: the
standard library and skillspector only, nothing from ``app``. The API's own scans reuse its
baseline helpers.

Events, each on its own line after PREFIX:
- ``{"event": "start", "skillspector_version": "..."}``
- ``{"event": "step", "node": "..."}``: a graph node finished
- ``{"event": "log", "line": "INFO ..."}``: a skillspector log record
- ``{"event": "report", "report": {...}}``: the finished report, exit code 0. Its
  ``generated_baseline`` holds a baseline accepting every active finding, when one could be made.
  For a repository holding several skills, ``skills`` lists each skill's own report
  (see run_scan)
- ``{"event": "error", "message": "..."}``: the scan failed, exit code 1
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlsplit

PREFIX = "@@skillspector-web@@ "


def emit(event: str, **data: Any) -> None:
    sys.stdout.write(PREFIX + json.dumps({"event": event, **data}) + "\n")
    sys.stdout.flush()


class _EventLogHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        emit("log", line=self.format(record))


def baseline_state(path: str | None) -> dict[str, Any]:
    """The graph state that applies the baseline at path; nothing without one.

    Raises ValueError for a baseline skillspector can't load.
    """
    if path is None:
        return {}
    from skillspector.suppression import load_baseline

    return {"baseline": load_baseline(path), "show_suppressed": True}


def scan_report(final_state: dict[str, Any] | None) -> dict[str, Any]:
    """The finished report, with a baseline accepting each of its active findings.

    The baseline is made here because its exact fingerprints need the scanned files' contents,
    which only exist while the scan runs (skillspector's `skillspector baseline` does the same).
    """
    import skillspector
    from skillspector.suppression import build_baseline_dict, effective_findings

    final_state = final_state or {}
    report = json.loads(final_state.get("report_body") or "{}")
    findings = effective_findings(final_state)
    if findings:
        try:
            report["generated_baseline"] = build_baseline_dict(
                findings,
                file_cache=final_state.get("local_file_cache") or final_state.get("file_cache") or {},
                scanner_version=skillspector.__version__,
            )
        except ValueError:
            # Some findings can't be fingerprinted exactly (no source content); offer none.
            pass
    return report


# Repositories holding several skills: each folder with a SKILL.md, up to this deep, is scanned as
# a skill of its own (skillspector's own --recursive only looks one level down, at local folders).
MAX_SKILLS = 30
MAX_SKILL_DEPTH = 4
_SKIPPED_FOLDERS = {"node_modules", "venv", "__pycache__"}
# A skill isn't started with less time than this left before the deadline.
_MIN_SKILL_SECONDS = 20.0
_clock = time.monotonic
# Targets that are one file or archive: never several skills.
_FILE_SUFFIXES = {".md", ".zip", ".py", ".sh", ".js", ".ts", ".json", ".yaml", ".yml", ".txt"}


def _may_hold_several_skills(target: str) -> bool:
    parts = urlsplit(target)
    if not parts.scheme:
        return Path(target).is_dir()
    if parts.hostname == "raw.githubusercontent.com" or "/archive/" in parts.path:
        return False
    return PurePosixPath(parts.path).suffix.lower() not in _FILE_SUFFIXES


def find_skills(root: Path) -> list[Path]:
    """The folders under root holding a SKILL.md, outermost only; none when root is a skill itself.

    Hidden folders and symlinks are skipped, and the search stops past MAX_SKILLS + 1, so the caller
    can tell there were too many.
    """
    if (root / "SKILL.md").is_file():
        return []
    found: list[Path] = []
    for directory, folders, files in os.walk(root):
        here = Path(directory)
        depth = len(here.relative_to(root).parts)
        if depth and "SKILL.md" in files and not (here / "SKILL.md").is_symlink():
            found.append(here)
            folders[:] = []  # A skill's own subfolders are part of it.
            if len(found) > MAX_SKILLS:
                break
            continue
        keep = depth < MAX_SKILL_DEPTH
        folders[:] = sorted(f for f in folders if keep and not f.startswith(".") and f not in _SKIPPED_FOLDERS)
    return sorted(found)


def skill_name(folder: Path) -> str:
    """The `name:` in a SKILL.md's front matter, else the folder's name."""
    try:
        with open(folder / "SKILL.md", encoding="utf-8", errors="replace") as file:
            head = file.read(4096)
    except OSError:
        return folder.name
    if head.startswith("---"):
        for line in head.splitlines()[1:]:
            if line.strip() == "---":
                break
            key, _, value = line.partition(":")
            if key.strip() == "name" and value.strip():
                return value.strip().strip("\"'")[:100]
    return folder.name


def combine_reports(skills: list[dict[str, Any]], unscanned: list[dict[str, str]]) -> dict[str, Any]:
    """One report for a repository of several skills, with each skill's own under `skills`.

    The verdict is the riskiest skill's. Metadata is merged so AI review status and token usage
    read the same as for one skill, and the baseline accepts every skill's active findings.
    """
    reports = [entry["report"] for entry in skills if "report" in entry]
    if not reports:
        raise RuntimeError(next((entry["error"] for entry in skills if "error" in entry), "No skill could be scanned"))
    riskiest = max(reports, key=lambda report: report.get("risk_assessment", {}).get("score", 0))
    metas = [report.get("metadata") or {} for report in reports]
    metadata: dict[str, Any] = {
        "skillspector_version": metas[0].get("skillspector_version"),
        "llm_requested": any(meta.get("llm_requested") for meta in metas),
        "llm_available": all(meta.get("llm_available") for meta in metas),
        "meta_analysis_applied": all(meta.get("meta_analysis_applied") for meta in metas),
        "inference_usage": [record for meta in metas for record in meta.get("inference_usage") or []],
    }
    if any("llm_calls_attempted" in meta for meta in metas):
        metadata["llm_calls_attempted"] = sum(meta.get("llm_calls_attempted", 0) for meta in metas)
        metadata["llm_calls_succeeded"] = sum(meta.get("llm_calls_succeeded", 0) for meta in metas)
    if any(meta.get("llm_degraded") for meta in metas):
        metadata["llm_degraded"] = True
    errors = [meta["llm_error"] for meta in metas if meta.get("llm_error")]
    if errors:
        metadata["llm_error"] = errors[0]
    provenance = next((meta["llm_provenance"] for meta in metas if meta.get("llm_provenance")), None)
    if provenance:
        metadata["llm_provenance"] = provenance
    combined: dict[str, Any] = {
        # The page titles it from the target.
        "skill": {"name": "unknown", "source": "", "scanned_at": riskiest.get("skill", {}).get("scanned_at", "")},
        "risk_assessment": riskiest["risk_assessment"],
        "issues": [],
        "suppressed_count": sum(report.get("suppressed_count", 0) for report in reports),
        "execution_successful": len(reports) == len(skills)
        and not unscanned
        and all(report.get("execution_successful", True) for report in reports),
        "metadata": metadata,
        "skills": skills,
        "unscanned_skills": unscanned,
    }
    fingerprints = [
        entry for report in reports for entry in (report.get("generated_baseline") or {}).get("fingerprints", [])
    ]
    if fingerprints:
        first = next(report["generated_baseline"] for report in reports if report.get("generated_baseline"))
        combined["generated_baseline"] = {**first, "fingerprints": fingerprints}
    return combined


# skillspector's CLI, which alone implements following references (--transitive).
_CLI = "import sys; from skillspector.cli import app; sys.argv[0] = 'skillspector'; app()"
# A log line from an analyzer node, e.g. "INFO [skillspector.nodes.analyzers.static_yara] ...".
_NODE_LOG = re.compile(r"^(?:INFO|WARNING) \[skillspector\.nodes\.(?:analyzers\.)?(\w+)\]")


def _scan_with_cli(
    input_path: str,
    *,
    use_llm: bool,
    baseline_path: str | None,
    transitive: dict[str, Any],
    step: Callable[[str], None],
    on_log: Callable[[str], None],
    max_seconds: float | None = None,
) -> dict[str, Any]:
    """Scan through skillspector's CLI, following references; its log stands in for graph steps."""
    from skillspector.graph import graph

    total_steps = len([node for node in graph.get_graph().nodes if node not in ("__start__", "__end__")])
    with tempfile.TemporaryDirectory() as directory:
        output = os.path.join(directory, "report.json")
        args = [sys.executable, "-c", _CLI, "scan", input_path, "--format", "json", "--output", output, "--verbose"]
        args += ["--transitive", "--transitive-depth", str(transitive["depth"])]
        for prefix in transitive.get("allow", []):
            args += ["--transitive-allow-prefix", prefix]
        for prefix in transitive.get("deny", []):
            args += ["--transitive-deny-prefix", prefix]
        if not use_llm:
            args.append("--no-llm")
        if baseline_path:
            args += ["--baseline", baseline_path]
        env = dict(os.environ)
        if max_seconds is not None:
            env["SKILLSPECTOR_MAX_WORKFLOW_SECONDS"] = f"{max_seconds:g}"
        seen: set[str] = set()
        last_line = ""
        with subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, env=env) as process:
            assert process.stderr is not None
            for raw in process.stderr:
                line = raw.rstrip()
                if not line or line.startswith("DEBUG"):
                    continue
                last_line = line
                on_log(line)
                node = _NODE_LOG.match(line)
                if node and node.group(1) not in seen and len(seen) < total_steps:
                    seen.add(node.group(1))
                    step(node.group(1))
        # 0 and 1 (a risky skill) both mean a report was written; 2 is an error.
        if process.returncode not in (0, 1) or not os.path.exists(output):
            raise RuntimeError(re.sub(r"\[/?[a-z ]+\]", "", last_line) or f"skillspector exited with {process.returncode}")
        with open(output, encoding="utf-8") as file:
            return json.load(file)


def run_scan(
    target: str,
    *,
    use_llm: bool,
    baseline_path: str | None = None,
    on_step: Callable[[str], None],
    on_log: Callable[[str], None],
    config: dict[str, Any] | None = None,
    deadline_seconds: float | None = None,
    transitive: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Scan target, splitting a repository that holds several skills into one scan per skill.

    on_step is called once per graph step of a single scan; for several skills, as many times
    spread over all of them, so progress still ends at the graph's step count. With
    deadline_seconds, skills are only started while there's time left for them. With transitive
    ({"depth", "allow", "deny"}), each scan also follows the skill's external references; it runs
    through skillspector's CLI, so it makes no baseline (that needs the scanned files' contents).
    """
    from skillspector.graph import graph

    base_state = {"output_format": "json", "use_llm": use_llm, **baseline_state(baseline_path)}

    def scan_one(input_path: str, step: Callable[[str], None], extra: dict[str, Any] | None = None) -> dict[str, Any]:
        if transitive:
            budget = (extra or {}).get("workflow_resource_budget")
            return _scan_with_cli(
                input_path,
                use_llm=use_llm,
                baseline_path=baseline_path,
                transitive=transitive,
                step=step,
                on_log=on_log,
                max_seconds=budget.max_seconds if budget is not None else None,
            )
        final_state: dict[str, Any] | None = None
        for mode, chunk in graph.stream({**base_state, "input_path": input_path, **(extra or {})}, config=config, stream_mode=["updates", "values"]):
            if mode == "updates":
                for node_name in chunk:
                    step(node_name)
            elif mode == "values":
                final_state = chunk
        return scan_report(final_state)

    started = _clock()
    skills: list[Path] = []
    root: Path | None = None
    handler = None
    if _may_hold_several_skills(target):
        from skillspector.input_handler import InputHandler

        handler = InputHandler()
        try:
            root, _kind = handler.resolve(target)
            skills = find_skills(root) if root.is_dir() else []
        except Exception:  # noqa: BLE001
            # The scan itself reports a target it can't fetch, as before.
            root, skills = None, []
    try:
        if len(skills) < 2:
            # Following references, skillspector's CLI charges the target's own download to the
            # traversal's 10 MB budget, which one repository clone can use up: scan the copy
            # fetched above instead, so the budget goes to what the skill references.
            return scan_one(str(root) if transitive and root is not None else target, on_step)
        if len(skills) > MAX_SKILLS:
            raise RuntimeError(f"This repository holds more than {MAX_SKILLS} skills: scan them one folder at a time")
        return _scan_each(root, skills, scan_one, on_step, on_log, started, deadline_seconds)
    finally:
        if handler is not None:
            handler.cleanup()


def _scan_each(root, skills, scan_one, on_step, on_log, started, deadline_seconds) -> dict[str, Any]:
    from skillspector.graph import graph
    from skillspector.state import WorkflowResourceBudget

    total_steps = len([node for node in graph.get_graph().nodes if node not in ("__start__", "__end__")])
    emitted = 0
    entries: list[dict[str, Any]] = []
    unscanned: list[dict[str, str]] = []
    on_log(f"Found {len(skills)} skills: scanning each one")
    for index, folder in enumerate(skills):
        path, name = folder.relative_to(root).as_posix(), skill_name(folder)
        extra: dict[str, Any] = {}
        if deadline_seconds is not None:
            remaining = deadline_seconds - (_clock() - started)
            if remaining < _MIN_SKILL_SECONDS:
                unscanned.append({"path": path, "name": name, "reason": "The scan ran out of time before this skill"})
                continue
            # A fair share of what's left, so one large skill can't use up every other skill's time:
            # it ends partly inspected instead, and says so.
            share = max(remaining / (len(skills) - index), _MIN_SKILL_SECONDS)
            extra["workflow_resource_budget"] = WorkflowResourceBudget(max_seconds=min(share, remaining))
        on_log(f"Scanning skill {index + 1} of {len(skills)}: {path}")
        done = 0

        def step(node_name: str, index: int = index) -> None:
            nonlocal done, emitted
            done = min(done + 1, total_steps)
            # Progress over every skill, scaled to one scan's step count.
            while emitted < (index * total_steps + done) // len(skills):
                emitted += 1
                on_step(node_name)

        try:
            entries.append({"path": path, "name": name, "report": scan_one(str(folder), step, extra)})
        except Exception as exc:  # noqa: BLE001
            on_log(f"Skill {path} failed: {exc}")
            entries.append({"path": path, "name": name, "error": str(exc)})
    return combine_reports(entries, unscanned)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="sandbox_runner.py")
    parser.add_argument("target")
    parser.add_argument("--llm", action="store_true")
    parser.add_argument("--baseline")
    parser.add_argument("--transitive-depth", type=int)
    parser.add_argument("--transitive-allow", action="append", default=[])
    parser.add_argument("--transitive-deny", action="append", default=[])
    try:
        args = parser.parse_args(argv[1:])
    except SystemExit:
        return 2
    target, use_llm = args.target, args.llm

    import skillspector

    # Attached after the import, like the API does, so only this scan's records are reported.
    handler = _EventLogHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    logger = logging.getLogger("skillspector")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)

    emit("start", skillspector_version=skillspector.__version__)
    # The sandbox sets skillspector's deadline under its own limit (app/sandbox_executor.py); several
    # skills share it.
    deadline = os.environ.get("SKILLSPECTOR_MAX_WORKFLOW_SECONDS")
    try:
        report = run_scan(
            target,
            use_llm=use_llm,
            baseline_path=args.baseline,
            on_step=lambda node: emit("step", node=node),
            on_log=lambda line: emit("log", line=line),
            deadline_seconds=float(deadline) if deadline else None,
            transitive={"depth": args.transitive_depth, "allow": args.transitive_allow, "deny": args.transitive_deny}
            if args.transitive_depth
            else None,
        )
        emit("report", report=report)
        return 0
    except Exception as exc:  # noqa: BLE001
        emit("error", message=str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
