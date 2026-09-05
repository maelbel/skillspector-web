import type { ScanHistoryResponse } from '~~/shared/types/scan'

export default defineEventHandler(async (event) => {
  const { limit, offset } = getQuery<{ limit?: string, offset?: string }>(event)
  const { apiBase } = useRuntimeConfig()

  return await $fetch<ScanHistoryResponse>('/scan', {
    baseURL: apiBase,
    query: { limit, offset }
  }).catch((error) => {
    throw createError({
      statusCode: error?.response?.status ?? 502,
      statusMessage: error?.data?.detail ?? 'Failed to fetch scan history'
    })
  })
})
