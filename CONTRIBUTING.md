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
