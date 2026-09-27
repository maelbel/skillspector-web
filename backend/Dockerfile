FROM python:3.13-slim AS base

# git: uv fetches skillspector from GitHub, and skillspector clones Git scan targets.
# Every locked dependency ships prebuilt wheels, so no compiler toolchain is needed.
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

ARG CLAUDE_CODE_VERSION=2.1.259
COPY --from=node:22-bookworm-slim /usr/local/bin/node /usr/local/bin/node
COPY --from=node:22-bookworm-slim /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -s /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx \
    && npm install -g @anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}

ARG UV_VERSION=0.12.9
RUN pip install --no-cache-dir uv==${UV_VERSION}
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

FROM base AS development
COPY . .
RUN uv sync --frozen
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

FROM base AS production
COPY . .
RUN uv sync --frozen --no-dev
CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
