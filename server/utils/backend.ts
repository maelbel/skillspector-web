import type { H3Event } from 'h3'
import type { NitroFetchOptions, NitroFetchRequest } from 'nitropack'

type BackendOptions = NitroFetchOptions<NitroFetchRequest> & {
  // Shown when the API gives no message of its own.
  fallbackMessage: string
}

// FastAPI returns `detail` as a string, or as a list of validation errors.
function errorMessage(data: unknown, fallback: string): string {
  const detail = (data as { detail?: unknown } | undefined)?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && typeof detail[0]?.msg === 'string') return detail[0].msg
  return fallback
}

/**
 * Call the API on behalf of the browser: forwards the client IP (for rate limits) and the session
 * cookie (as a bearer token), and turns API errors into h3 errors with the API's message.
 */
export async function backendFetch<T>(event: H3Event, path: string, options: BackendOptions): Promise<T> {
  const { apiBase } = useRuntimeConfig()
  const { fallbackMessage, headers, ...rest } = options
  const token = getSessionToken(event)

  try {
    return await $fetch<T>(path, {
      ...rest,
      baseURL: apiBase,
      headers: {
        ...(headers as Record<string, string> | undefined),
        'X-Forwarded-For': getClientIp(event),
        ...(token ? { Authorization: `Bearer ${token}` } : {})
      }
    } as NitroFetchOptions<NitroFetchRequest>) as T
  } catch (error) {
    const { response, data } = (error ?? {}) as { response?: { status?: number }, data?: unknown }
    const statusCode = response?.status ?? 502
    // An expired or revoked session: drop the cookie so the next page asks to sign in again.
    if (statusCode === 401 && token) clearSessionToken(event)
    throw createError({ statusCode, statusMessage: errorMessage(data, fallbackMessage) })
  }
}
