# skillspector-web-api

Thin FastAPI wrapper around [skillspector](https://github.com/NVIDIA/skillspector)'s
own LangGraph scan pipeline (`skillspector.graph.graph`) — no CLI subprocess involved.

## Endpoints

- `GET /health` — status, skillspector version, whether an LLM provider is configured.
- `POST /scan` — `{ "target": "https://github.com/...", "use_llm": false }` → `{ id, status }`.
  `target` must be an `http(s)` URL (Git repo, zip, or raw file) — local paths are rejected so
  the API can't be used to scan the container's own filesystem.
- `GET /scan/{id}` — job status (`pending` / `running` / `done` / `error`) and, once `done`,
  the parsed JSON report (`skillspector`'s `--format json` shape: `risk_assessment`, `issues`, …).

## Local dev

```bash
uv sync
uv run uvicorn app.main:app --reload
```

## Notes

- Jobs live in an in-memory dict (`app/scanner.py`) — single process, no persistence. Fine for
  one homelab replica; swap for a real queue before running more than one.
- Each scan is bounded by skillspector's own workflow budget (~60s / 64MB), enforced inside the
  graph itself — no extra timeout needed here.
- LLM-based semantic analysis is off by default (`use_llm: false`) to avoid burning API budget on
  arbitrary user-submitted targets. Set `SKILLSPECTOR_PROVIDER` / provider API key env vars to
  make it available.
