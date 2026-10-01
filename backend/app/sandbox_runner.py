"""Run one skillspector scan and report on stdout, one tagged JSON event per line.

This file is uploaded into a Vercel Sandbox and run there with
``python3 sandbox_runner.py <target> [--llm] [--baseline FILE]`` (``--llm`` adds skillspector's AI
review; ``--baseline`` suppresses the findings a baseline accepts), so it must stay standalone: the
standard library and skillspector only, nothing from ``app``. The API's own scans reuse its
baseline helpers.

Events, each on its own line after PREFIX:
- ``{"event": "start", "skillspector_version": "..."}``
- ``{"event": "step", "node": "..."}``: a graph node finished
- ``{"event": "log", "line": "INFO ..."}``: a skillspector log record
- ``{"event": "report", "report": {...}}``: the finished report, exit code 0. Its
  ``generated_baseline`` holds a baseline accepting every active finding, when one could be made
- ``{"event": "error", "message": "..."}``: the scan failed, exit code 1
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import Any

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


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="sandbox_runner.py")
    parser.add_argument("target")
    parser.add_argument("--llm", action="store_true")
    parser.add_argument("--baseline")
    try:
        args = parser.parse_args(argv[1:])
    except SystemExit:
        return 2
    target, use_llm = args.target, args.llm

    import skillspector
    from skillspector.graph import graph

    # Attached after the import, like the API does, so only this scan's records are reported.
    handler = _EventLogHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    logger = logging.getLogger("skillspector")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)

    emit("start", skillspector_version=skillspector.__version__)
    try:
        final_state: dict[str, Any] | None = None
        state = {"input_path": target, "output_format": "json", "use_llm": use_llm, **baseline_state(args.baseline)}
        for mode, chunk in graph.stream(state, stream_mode=["updates", "values"]):
            if mode == "updates":
                for node_name in chunk:
                    emit("step", node=node_name)
            elif mode == "values":
                final_state = chunk
        emit("report", report=scan_report(final_state))
        return 0
    except Exception as exc:  # noqa: BLE001
        emit("error", message=str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
