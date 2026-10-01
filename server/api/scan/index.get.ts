import type { ScanHistoryResponse } from '~~/shared/types/scan'

export default defineEventHandler(async (event) => {
  // target: only that target's scans, its timeline.
  const { limit, offset, target } = getQuery<{ limit?: string, offset?: string, target?: string }>(event)

  return await backendFetch<ScanHistoryResponse>(event, '/scan', {
    query: { limit, offset, target },
    fallbackMessage: 'Failed to fetch scan history'
  })
})
