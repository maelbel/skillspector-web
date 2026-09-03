import type { ScanStatus } from '~~/shared/types/scan'

const POLL_INTERVAL_MS = 2000

export function useScanStatus(id: string) {
  const { data: status, error, refresh } = useFetch<ScanStatus>(`/api/scan/${id}`, {
    key: `scan-${id}`
  })

  let timer: ReturnType<typeof setTimeout> | undefined

  function scheduleNextPoll() {
    const current = status.value
    if (!current || current.status === 'pending' || current.status === 'running') {
      timer = setTimeout(async () => {
        await refresh()
        scheduleNextPoll()
      }, POLL_INTERVAL_MS)
    }
  }

  onMounted(scheduleNextPoll)
  onUnmounted(() => {
    if (timer) clearTimeout(timer)
  })

  return { status, error }
}
