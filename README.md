# skillspector-web

A web UI for [NVIDIA/skillspector](https://github.com/NVIDIA/skillspector) — paste a skill's
repo/zip/file URL, get a risk score and finding list back, without touching the CLI.

## How it's put together

- **`backend/`** — a small FastAPI service that imports skillspector as a library and calls its
  compiled LangGraph pipeline directly (`skillspector.graph.graph.invoke(...)`), the same way the
  `skillspector` CLI does internally. No subprocess, no CLI parsing. See `backend/README.md`.
- **root (`app/`, `server/`)** — a Nuxt 4 + Nuxt UI frontend. The Nitro `server/api/*` routes are
  a thin same-origin proxy to the backend so the browser never talks to it directly.

```
POST /api/scan        (Nuxt) --> POST /scan        (FastAPI) --> graph.invoke(...) in a job
GET  /api/scan/[id]    (Nuxt) --> GET  /scan/{id}    (FastAPI) --> job status + parsed report
```

## Local development (no Docker)

```bash
# backend
cd backend
uv sync
uv run uvicorn app.main:app --reload

# frontend, in a second terminal
cd ..
pnpm install
NUXT_API_BASE=http://localhost:8000 pnpm dev
```

Open http://localhost:3000.

## Docker

```bash
docker compose up --build
```

Serves the UI on http://localhost:3005. `api` is never published — only `web` talks to it, over
the internal Docker network.

Edit `backend/.env.local` first if you want the "use LLM analysis" toggle available (set
`SKILLSPECTOR_PROVIDER` + the matching provider API key — see skillspector's own README). If you
set `SKILLSPECTOR_PROVIDER=claude_cli`, note the backend image doesn't install the Claude CLI —
static analysis still works, but the toggle will error until that's added.

For exposing this behind a real domain/TLS (Traefik or otherwise), see
[docs/REVERSE_PROXY.md](./docs/REVERSE_PROXY.md) — that config goes in a gitignored
`docker-compose.override.yml`, not into `docker-compose.yml` itself.

## Known limitations

- Scan jobs live in the backend's memory (`backend/app/scanner.py`) — restarting the API loses
  in-flight/queued scans, and this can't run as more than one replica as-is.
- No auth — same posture as this homelab's other internal tools; put it behind the proxy network
  only if that's not desired for a given deployment.
- `target` is restricted to `http(s)` URLs; local-path/zip-upload scanning isn't wired up (would
  need a file upload endpoint on the backend).

## License

[MIT](./LICENSE) for this project's own code. It depends on
[NVIDIA/skillspector](https://github.com/NVIDIA/skillspector) (Apache-2.0) as a library, installed
via pip — not vendored — so skillspector's license terms apply to that dependency separately.
