<script setup lang="ts">
import type { UsageResponse } from '~~/shared/types/settings'

const { data: usage } = await useFetch<UsageResponse>('/api/account/usage')

const limits = computed(() => {
  const value = usage.value
  if (!value?.quotas_apply) return []
  return [
    { label: 'Scans in the last 24 hours', used: value.scans_today, limit: value.daily_scan_quota },
    { label: 'Scans in progress', used: value.active_scans, limit: value.concurrent_scan_quota }
  ].filter(row => row.limit !== null) as { label: string, used: number, limit: number }[]
})
</script>

<template>
  <UCard
    v-if="usage && (usage.scans_paused || limits.length)"
    :ui="{ root: 'rounded-xs', body: 'p-5 sm:p-6' }"
  >
    <div class="flex flex-col gap-4">
      <div>
        <h2 class="text-lg font-semibold tracking-tight text-highlighted">
          Usage
        </h2>
        <p class="mt-1 text-sm text-muted">
          How many scans you can start on this server. Deleting a scan doesn't give it back.
        </p>
      </div>

      <UAlert
        v-if="usage.scans_paused"
        color="warning"
        variant="subtle"
        icon="i-lucide-circle-pause"
        title="New scans are paused on this server"
        description="An admin has paused scanning for everyone. Your history is still here."
      />

      <div
        v-for="row in limits"
        :key="row.label"
        class="flex flex-col gap-1.5"
      >
        <div class="flex items-baseline justify-between gap-3 text-sm">
          <span class="text-default">{{ row.label }}</span>
          <span class="font-mono text-xs text-muted tabular-nums">{{ Math.min(row.used, row.limit) }} of {{ row.limit }}</span>
        </div>
        <UProgress
          :model-value="Math.min(row.used, row.limit)"
          :max="row.limit"
          :color="row.used >= row.limit ? 'warning' : 'neutral'"
          size="sm"
        />
      </div>
    </div>
  </UCard>
</template>
