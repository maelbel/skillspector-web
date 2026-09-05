import type { ScanLogsResponse } from '~~/shared/types/scan'

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')
  if (!id) {
    throw createError({ statusCode: 400, statusMessage: 'Missing scan id' })
  }

  const { apiBase } = useRuntimeConfig()

  return await $fetch<ScanLogsResponse>(`/scan/${id}/logs`, { baseURL: apiBase }).catch((error) => {
    throw createError({
      statusCode: error?.response?.status ?? 502,
      statusMessage: error?.data?.detail ?? 'Failed to fetch scan logs'
    })
  })
})
