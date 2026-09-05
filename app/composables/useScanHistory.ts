import type { ScanHistoryResponse } from '~~/shared/types/scan'

const PAGE_SIZE = 20

export function useScanHistory() {
  const limit = ref(PAGE_SIZE)

  const { data, status, error, refresh } = useFetch<ScanHistoryResponse>('/api/scan', {
    key: 'scan-history',
    query: { limit }
  })

  const hasMore = computed(() => (data.value?.items.length ?? 0) < (data.value?.total ?? 0))

  function loadMore() {
    limit.value += PAGE_SIZE
  }

  return { data, status, error, refresh, hasMore, loadMore }
}
