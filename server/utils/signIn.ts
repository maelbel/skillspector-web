import type { H3Event } from 'h3'
import type { User } from '~~/shared/types/auth'

interface TokenResponse {
  token: string
  expires_at: number
  user: User
}

/** Sign in through one of the API's credential endpoints and keep the session in the cookie. */
export async function signIn(event: H3Event, path: '/auth/login' | '/auth/setup' | '/auth/signup', fallbackMessage: string) {
  const { email, password } = await readBody<{ email?: string, password?: string }>(event)
  if (!email || !password) {
    throw createError({ statusCode: 400, statusMessage: 'Enter your email and password' })
  }

  const { token, expires_at: expiresAt, user } = await backendFetch<TokenResponse>(event, path, {
    method: 'POST',
    body: { email, password },
    fallbackMessage
  })
  setSessionToken(event, token, (expiresAt - Date.now() / 1000) / 86400)
  return { user }
}
