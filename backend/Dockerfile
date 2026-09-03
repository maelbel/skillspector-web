FROM python:3.13-slim AS base

# git: skillspector clones scanned repos. gcc/build-essential: yara-python
# falls back to a source build when no prebuilt wheel matches the platform.
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv
WORKDIR /app
COPY pyproject.toml ./
RUN uv sync --no-install-project

# --- development: live-reload, code comes from a bind mount ---
FROM base AS development
COPY . .
RUN uv sync
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# --- production: code baked into the image ---
FROM base AS production
COPY . .
RUN uv sync
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
