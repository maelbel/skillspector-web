import type { H3Event } from 'h3'

// With NUXT_TRUST_PROXY=true, trust only the right-most X-Forwarded-For entry: the one the
// reverse proxy in front of us appended. Anything to its left was supplied by the client.
// Without a proxy, X-Forwarded-For is entirely client-controlled, so use the socket address.
export function getClientIp(event: H3Event): string {
  const { trustProxy } = useRuntimeConfig(event)
  if (trustProxy) {
    const proxied = getRequestHeader(event, 'x-forwarded-for')
      ?.split(',')
      .map(part => part.trim())
      .filter(Boolean)
      .at(-1)
    if (proxied) return proxied
  }
  return getRequestIP(event) ?? 'unknown'
}
