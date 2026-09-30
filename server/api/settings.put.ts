import type { SettingsResponse } from '~~/shared/types/settings'

export default defineEventHandler(async (event) => {
  const { scanRetentionDays } = await readBody<{ scanRetentionDays?: number | null }>(event)

  return await backendFetch<SettingsResponse>(event, '/settings', {
    method: 'PUT',
    body: { scan_retention_days: scanRetentionDays ?? null },
    fallbackMessage: 'Failed to update settings'
  })
})
