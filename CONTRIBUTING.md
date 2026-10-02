# Contributing

Thanks for helping improve Skillspector Web. Issues and pull requests are welcome.

## Development setup

```bash
pnpm install
pnpm setup                 # choose "Local processes"

cd backend && uv run uvicorn app.main:app --reload            # API on :8000
NUXT_API_BASE=http://localhost:8000 pnpm dev                  # UI on :3000
```

Requirements: Node.js 22 with pnpm, Python 3.12–3.14 with [uv](https://docs.astral.sh/uv/).

> [!TIP]
> If you also run the Docker Compose stack from the same checkout, run backend commands inside the
> container (`docker exec skillspector-api uv run pytest`). The dev containers bind-mount the
> repository, so a host-side `uv` or `pnpm install` rewrites the environment the running containers
> depend on.

## Checks

CI runs all of these on every pull request; please run them before pushing.

| Area | Command |
|---|---|
| Frontend lint | `pnpm lint` |
| Frontend types | `pnpm typecheck` |
| Frontend tests | `pnpm test` |
| Frontend build | `pnpm build` |
| Backend lint | `cd backend && uv run ruff check .` |
| Backend tests | `cd backend && uv run pytest` |

CI also builds both Docker `production` targets.

## Screenshots

The README's screenshots (`docs/assets/screenshot-*.png`) come from `pnpm screenshots`
([`scripts/screenshots.mjs`](./scripts/screenshots.mjs)): the home page, a result, the Account page
and the backoffice, in both themes. Retake them after a UI change.

Run it against a server of its own, never one with real users: on an empty database it creates
`admin@example.com` and `alex@example.com` and scans a few public example skills as Alex. Give that
server accounts, quotas (so the Account page shows usage) and a throwaway `SECRET_KEY` (so it shows
the Claude key), and nothing from your `.env.local`:

```bash
# An API on its own database, next to the dev stack (docker compose up).
docker run -d --name skillspector-shots-api --network skillspector-web_internal --network-alias shots-api \
  -v "$PWD/backend:/app" -v /dev/null:/app/.env.local:ro -v skillspector-shots-data:/tmp/shots \
  -e SKILLSPECTOR_WEB_AUTH=accounts -e SKILLSPECTOR_WEB_DB_PATH=/tmp/shots/scans.db \
  -e SKILLSPECTOR_WEB_DAILY_SCAN_QUOTA=20 -e SKILLSPECTOR_WEB_CONCURRENT_SCAN_QUOTA=2 \
  -e SKILLSPECTOR_WEB_SECRET_KEY="$(docker exec skillspector-api uv run --no-sync python -m app.secrets_box)" \
  skillspector-web-api uv run --no-sync uvicorn app.main:app --host 0.0.0.0 --port 8000

# A production build of the web app on it (the dev server adds its own overlay).
pnpm build && NUXT_API_BASE=http://shots-api:8000 PORT=3200 node .output/server/index.mjs  # in the web container

# The screenshots, with Playwright's own browser.
docker run --rm --network skillspector-web_internal --user "$(id -u):$(id -g)" -e HOME=/tmp \
  -e BASE_URL=http://skillspector-web:3200 -v "$PWD:/work" -w /work \
  mcr.microsoft.com/playwright:v1.63.0-noble node scripts/screenshots.mjs
```

Running it again reuses the scans, so their times read "minutes ago" rather than "seconds ago".
Then `docker rm -f skillspector-shots-api && docker volume rm skillspector-shots-data`.

## Pull requests

- Keep each pull request to one change, with tests when behaviour changes.
- Use [Conventional Commits](https://www.conventionalcommits.org/) for commit messages and pull
  request titles — `feat:`, `fix:`, `docs:`, `test:`, `build:`, `chore:`. Pull requests are
  squash-merged, and [release-please](https://github.com/googleapis/release-please) derives the
  changelog and the next version from these prefixes.
- Match the surrounding code style: the ESLint config (via `@nuxt/eslint`) for the frontend,
  Ruff for the backend.

## Releases

Merging to `main` updates a release pull request maintained by release-please. Merging that pull
request tags the release, publishes the changelog and bumps the version in `package.json`,
`backend/pyproject.toml`, `backend/uv.lock` and the API's reported version.
