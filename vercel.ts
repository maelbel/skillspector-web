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
  rewrites: [
    // BotID (scan submissions, see server/utils/botId.ts) loads its challenge from these paths,
    // which must be rewritten to Vercel at the edge: proxied through a function, the challenge
    // doesn't see the browser and every visitor is classified as a bot. The paths are botid's
    // own, from node_modules/botid/dist/nuxt/module.mjs; test/vercel.test.ts fails if an upgrade
    // changes them. Plain strings only: Vercel's cloud build drops values it has to compute.
    {
      source: '/149e9513-01fa-4fb0-aad4-566afd725d1b/2d206a39-8ed7-437e-a3be-862e0f06eea3/a-4-a/c.js',
      destination: 'https://api.vercel.com/bot-protection/v1/challenge'
    },
    {
      source: '/149e9513-01fa-4fb0-aad4-566afd725d1b/2d206a39-8ed7-437e-a3be-862e0f06eea3/:path*',
      destination: 'https://api.vercel.com/bot-protection/v1/proxy/:path*'
    },
    { source: '/(.*)', destination: { service: 'web' } }
  ],
  git: {
    // Only main (preprod) and production deploy by themselves; production is the release tag the
    // Deploy production workflow points it at. Previews of other branches share preprod's database,
    // where their migrations would run before review, so they're deployed by hand
    // (docs/VERCEL.md). A branch matching any `true` rule deploys; '**' also matches slashes.
    deploymentEnabled: { '**': false, 'main': true, 'production': true }
  },
  crons: [
    // Retention sweep (server/api/internal/retention.get.ts). Daily, the most often every Vercel
    // plan allows; changing the retention from the admin page also sweeps straight away.
    { path: '/api/internal/retention', schedule: '0 3 * * *' }
  ]
}
