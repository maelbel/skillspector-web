import type { AnalyticsEvents } from '~/utils/analytics'

type Track = <Name extends keyof AnalyticsEvents>(name: Name, data?: AnalyticsEvents[Name]) => void

declare module '#app' {
  interface NuxtApp {
    // Only on the hosted version (app/analytics/vercel.client.ts).
    $track?: Track
  }
}

/** Track a Web Analytics event; does nothing where analytics is off (self-hosted). Call it in
 * setup, and the function it returns whenever. */
export function useAnalytics(): { track: Track } {
  const nuxtApp = useNuxtApp()
  return { track: (name, data) => nuxtApp.$track?.(name, data) }
}
