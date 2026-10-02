import { inject, pageview, track } from '@vercel/analytics'
import type { AnalyticsEvents } from '~/utils/analytics'

// Vercel Web Analytics, on the hosted version only: nuxt.config.ts registers this plugin when
// NUXT_PUBLIC_ANALYTICS is true at build time, so self-hosted builds hold none of it and make no
// request to Vercel. Cookieless. Page views and events name the route's pattern, never its path or
// query (app/utils/analytics.ts); useAnalytics() tracks the events.
export default defineNuxtPlugin(() => {
  const router = useRouter()
  const patternOf = (path: string) => routePattern(router.resolve(path).matched.at(-1)?.path)

  inject({
    framework: 'nuxt',
    // Page views are sent below, with the route's pattern, rather than on every pushState.
    disableAutoTrack: true,
    beforeSend: event => ({ ...event, url: anonymousUrl(event.url, patternOf) })
  })

  const view = (path: string) => {
    const route = patternOf(path)
    pageview({ route, path: route })
  }
  onNuxtReady(() => view(router.currentRoute.value.path))
  router.afterEach((to, from) => {
    if (to.path !== from.path) view(to.path)
  })

  return {
    provide: {
      track: <Name extends keyof AnalyticsEvents>(name: Name, data?: AnalyticsEvents[Name]) => track(name, data)
    }
  }
})
