import type { SettingsResponse } from '~~/shared/types/settings'

export default defineEventHandler(async () => {
  const { apiBase } = useRuntimeConfig()

  return await $fetch<SettingsResponse>('/settings', { baseURL: apiBase }).catch((error) => {
    throw createError({
      statusCode: error?.response?.status ?? 502,
      statusMessage: error?.data?.detail ?? 'Failed to fetch settings'
    })
  })
})
