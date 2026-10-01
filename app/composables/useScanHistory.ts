import type { ScanHistoryResponse } from '~~/shared/types/scan'

const PAGE_SIZE = 20

export type HistorySort = 'created_at' | 'target' | 'risk_score' | 'verdict' | 'status'
export type SortOrder = 'asc' | 'desc'

/**
 * The history, sorted by the API so paging stays right (newest first by default); with target,
 * only that target's scans (its timeline).
 */
export function useScanHistory(
  target?: Ref<string | undefined>,
  sort?: Ref<HistorySort>,
  order?: Ref<SortOrder>
) {
  const limit = ref(PAGE_SIZE)

  const { data, status, error, refresh } = useFetch<ScanHistoryResponse>('/api/scan', {
    key: 'scan-history',
    query: { limit, target, sort, order }
  })

  const hasMore = computed(() => (data.value?.items.length ?? 0) < (data.value?.total ?? 0))

  function loadMore() {
    limit.value += PAGE_SIZE
  }

  return { data, status, error, refresh, hasMore, loadMore }
}
