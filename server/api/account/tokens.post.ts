import type { CreatedApiToken } from '~~/shared/types/auth'

// A new API token: the only response that ever holds the token itself.
export default defineEventHandler(async (event) => {
  const { name, expiresInDays } = await readBody<{ name?: string, expiresInDays?: number | null }>(event)
  return await backendFetch<CreatedApiToken>(event, '/account/tokens', {
    method: 'POST',
    body: { name: typeof name === 'string' ? name : '', expires_in_days: typeof expiresInDays === 'number' ? expiresInDays : null },
    fallbackMessage: 'Failed to create the API token'
  })
})
