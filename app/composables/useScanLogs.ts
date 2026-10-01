import type { ScanLogsResponse } from '~~/shared/types/scan'

const POLL_INTERVAL_MS = 2000

/** A running scan's live log; none without an id (a shared result, whose log isn't shared). */
export function useScanLogs(id: string | null, isActive: Ref<boolean>) {
  const { data, error, refresh } = useFetch<ScanLogsResponse>(`/api/scan/${id}/logs`, {
    key: `scan-logs-${id}`,
    immediate: id !== null
  })

  let timer: ReturnType<typeof setTimeout> | undefined

  function scheduleNextPoll() {
    if (id === null) return
    timer = setTimeout(async () => {
      await refresh()
      if (isActive.value) scheduleNextPoll()
    }, POLL_INTERVAL_MS)
  }

  onMounted(scheduleNextPoll)
  onUnmounted(() => {
    if (timer) clearTimeout(timer)
  })

  const lines = computed(() => data.value?.lines ?? [])

  return { lines, error }
}
