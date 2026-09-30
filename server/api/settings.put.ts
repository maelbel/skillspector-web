import type { SettingsResponse } from '~~/shared/types/settings'

export default defineEventHandler(async (event) => {
  const body = await readBody<{ scanRetentionDays?: number | null, allowSignup?: boolean }>(event)

  // Only what was sent changes.
  const update: Record<string, unknown> = {}
  if ('scanRetentionDays' in body) update.scan_retention_days = body.scanRetentionDays ?? null
  if (typeof body.allowSignup === 'boolean') update.allow_signup = body.allowSignup

  return await backendFetch<SettingsResponse>(event, '/settings', {
    method: 'PUT',
    body: update,
    fallbackMessage: 'Failed to update settings'
  })
})
