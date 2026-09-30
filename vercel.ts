// The hosted deployment: one Vercel project running two services. Docker Compose installs don't
// read this file. Plain object rather than @vercel/config's VercelConfig, whose types don't cover
// `services` yet.
export default {
  services: {
    // The Nuxt app, the only public service. Its Nitro routes under /api/* call the API over the
    // binding, whose deployment-aware URL Vercel puts in NUXT_API_BASE (read at runtime).
    web: {
      root: '.',
      framework: 'nuxtjs',
      bindings: [{ type: 'service', service: 'api', format: 'url', env: 'NUXT_API_BASE' }]
    },
    // FastAPI. Private: no rewrite below reaches it, so the browser never calls it directly.
    // backend/pyproject.toml's [tool.vercel] names the app and the scan queue's subscriber; with
    // any other entrypoint, Vercel skips the subscriber.
    api: {
      root: 'backend',
      entrypoint: 'pyproject.toml'
    }
  },
  rewrites: [{ source: '/(.*)', destination: { service: 'web' } }],
  crons: [
    // Retention sweep (server/api/internal/retention.get.ts). Daily, the most often every Vercel
    // plan allows; changing the retention from the admin page also sweeps straight away.
    { path: '/api/internal/retention', schedule: '0 3 * * *' }
  ]
}
