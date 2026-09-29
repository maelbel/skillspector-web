import type { ScanLogsResponse } from '~~/shared/types/scan'

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')
  if (!id) {
    throw createError({ statusCode: 400, statusMessage: 'Missing scan id' })
  }

  return await backendFetch<ScanLogsResponse>(event, `/scan/${encodeURIComponent(id)}/logs`, {
    fallbackMessage: 'Failed to fetch scan logs'
  })
})
