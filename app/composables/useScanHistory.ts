import type { ScanHistoryResponse } from '~~/shared/types/scan'

const PAGE_SIZE = 20

/** The history, newest first; with target, only that target's scans (its timeline). */
export function useScanHistory(target?: Ref<string | undefined>) {
  const limit = ref(PAGE_SIZE)

  const { data, status, error, refresh } = useFetch<ScanHistoryResponse>('/api/scan', {
    key: 'scan-history',
    query: { limit, target }
  })

  const hasMore = computed(() => (data.value?.items.length ?? 0) < (data.value?.total ?? 0))

  function loadMore() {
    limit.value += PAGE_SIZE
  }

  return { data, status, error, refresh, hasMore, loadMore }
}
