"""Run one skillspector scan and report on stdout, one tagged JSON event per line.

This file is uploaded into a Vercel Sandbox and run there with
``python3 sandbox_runner.py <target> [--llm]`` (``--llm`` adds skillspector's AI review),
so it must stay standalone: the standard library and skillspector only, nothing from ``app``.

Events, each on its own line after PREFIX:
- ``{"event": "start", "skillspector_version": "..."}``
- ``{"event": "step", "node": "..."}``: a graph node finished
- ``{"event": "log", "line": "INFO ..."}``: a skillspector log record
- ``{"event": "report", "report": {...}}``: the finished report, exit code 0
- ``{"event": "error", "message": "..."}``: the scan failed, exit code 1
"""

from __future__ import annotations

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


def main(argv: list[str]) -> int:
    if len(argv) not in (2, 3) or (len(argv) == 3 and argv[2] != "--llm"):
        sys.stderr.write("usage: sandbox_runner.py <target> [--llm]\n")
        return 2
    target = argv[1]
    use_llm = len(argv) == 3

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
        state = {"input_path": target, "output_format": "json", "use_llm": use_llm}
        for mode, chunk in graph.stream(state, stream_mode=["updates", "values"]):
            if mode == "updates":
                for node_name in chunk:
                    emit("step", node=node_name)
            elif mode == "values":
                final_state = chunk
        emit("report", report=json.loads((final_state or {}).get("report_body") or "{}"))
        return 0
    except Exception as exc:  # noqa: BLE001
        emit("error", message=str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
