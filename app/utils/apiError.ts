// The Nitro proxies return the backend's message as `statusMessage` in the JSON body; the
// FetchError's own `message` wraps it as `[POST] "/api/scan": 429 …`, which isn't for humans.
export function apiErrorMessage(err: unknown, fallback: string): string {
  const { data, response } = (err ?? {}) as {
    data?: { statusMessage?: string, message?: string }
    response?: unknown
  }
  const message = data?.statusMessage || data?.message
  if (message) {
    const text = message.replace(/^Value error, /, '')
    return text.charAt(0).toUpperCase() + text.slice(1)
  }
  if (err && typeof err === 'object' && 'data' in err && !response) {
    return 'Couldn’t reach the server — check your connection and try again.'
  }
  return fallback
}
