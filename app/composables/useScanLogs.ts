import type { ScanLogsResponse } from '~~/shared/types/scan'

const POLL_INTERVAL_MS = 2000

export function useScanLogs(id: string, isActive: Ref<boolean>) {
  const { data, error, refresh } = useFetch<ScanLogsResponse>(`/api/scan/${id}/logs`, {
    key: `scan-logs-${id}`
  })

  let timer: ReturnType<typeof setTimeout> | undefined

  function scheduleNextPoll() {
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
