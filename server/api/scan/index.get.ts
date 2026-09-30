import type { ScanHistoryResponse } from '~~/shared/types/scan'

export default defineEventHandler(async (event) => {
  const { limit, offset } = getQuery<{ limit?: string, offset?: string }>(event)

  return await backendFetch<ScanHistoryResponse>(event, '/scan', {
    query: { limit, offset },
    fallbackMessage: 'Failed to fetch scan history'
  })
})
