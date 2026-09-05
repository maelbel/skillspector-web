import type { SettingsResponse } from '~~/shared/types/settings'

export default defineEventHandler(async (event) => {
  const { adminToken, scanRetentionDays } = await readBody<{ adminToken?: string, scanRetentionDays?: number | null }>(event)

  if (!adminToken) {
    throw createError({ statusCode: 400, statusMessage: 'Missing "adminToken" in request body' })
  }

  const { apiBase } = useRuntimeConfig()

  return await $fetch<SettingsResponse>('/settings', {
    baseURL: apiBase,
    method: 'PUT',
    headers: { 'X-Admin-Token': adminToken },
    body: { scan_retention_days: scanRetentionDays ?? null }
  }).catch((error) => {
    throw createError({
      statusCode: error?.response?.status ?? 502,
      statusMessage: error?.data?.detail?.[0]?.msg ?? error?.data?.detail ?? 'Failed to update settings'
    })
  })
})
