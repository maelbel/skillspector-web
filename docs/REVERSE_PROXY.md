# Reverse proxy setup

`docker-compose.yml` publishes only the `web` service, on `3005` — enough to get started, but
not something you'd expose to the internet as-is (no TLS, no real hostname). The `api` service
is never published; `web`'s Nitro server is the only thing that talks to it, over the `internal`
network.

Putting a reverse proxy in front of `web` handles TLS termination and lets you serve it under a
real domain. This is entirely your call as the deployer — nothing here ships a proxy or assumes
one. You add it via `docker-compose.override.yml`, a file Docker Compose merges on top of
`docker-compose.yml` automatically and that's already gitignored (see `.gitignore`), so proxy
config with your real domain never risks landing in a commit.

Two things a proxy config needs to set on `web`, whichever proxy you use:

- **`NUXT_ALLOWED_HOST`** (env var) — your public hostname, e.g. `skillspector.example.com`.
  Vite's dev server (the `development` Docker target runs `nuxt dev`) rejects requests whose
  `Host` header isn't in its allowlist by default; without this you'll get "Blocked request. This
  host is not allowed." The `production` target's plain Node server has no such check.
- **`ports: !reset []`** — drop the published `3005:3000` mapping; the proxy reaches the
  container directly over the Docker network, so there's no need to expose it on the host too.

## Traefik

Assumes Traefik is already running elsewhere on the host (its own compose project) with the
Docker provider enabled, watching an external network named `proxy`, and a certresolver
configured for Let's Encrypt. Adjust the certresolver name and entrypoint to match your own
Traefik setup.

```yaml
# docker-compose.override.yml
services:
  web:
    ports: !reset []
    environment:
      NUXT_ALLOWED_HOST: skillspector.example.com
    networks:
      - proxy
    labels:
      - traefik.enable=true
      # Required because this container sits on two networks (proxy + internal,
      # the latter for reaching the api service) — otherwise Traefik's Docker
      # provider can't tell which network IP to route to.
      - traefik.docker.network=proxy
      - traefik.http.services.skillspector.loadbalancer.server.port=3000
      - traefik.http.routers.skillspector.rule=Host(`skillspector.example.com`)
      - traefik.http.routers.skillspector.entrypoints=websecure
      - traefik.http.routers.skillspector.tls=true
      - traefik.http.routers.skillspector.tls.certresolver=le

networks:
  proxy:
    external: true
```

Then `docker compose up -d --build` — Compose picks up the override automatically.
