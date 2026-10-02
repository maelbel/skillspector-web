import { injectSpeedInsights } from '@vercel/speed-insights'

// Vercel Speed Insights (Core Web Vitals from real visits), on the hosted version only:
// nuxt.config.ts registers this plugin when NUXT_PUBLIC_SPEED_INSIGHTS is true at build time, so
// self-hosted builds hold none of it. Like Web Analytics (vercel.client.ts), each measurement names
// the route's pattern, never its path or query (app/utils/analytics.ts).
export default defineNuxtPlugin(() => {
  const router = useRouter()
  const patternOf = (path: string) => routePattern(router.resolve(path).matched.at(-1)?.path)

  const insights = injectSpeedInsights({
    framework: 'nuxt',
    route: patternOf(router.currentRoute.value.path),
    beforeSend: event => ({ ...event, url: anonymousUrl(event.url, patternOf) })
  })
  router.afterEach(to => insights?.setRoute(patternOf(to.path)))
})
