<script setup lang="ts">
import type { ScanSummary } from '~~/shared/types/scan'

const SHOWN = 5

const { data } = useRecentScans()
const scans = computed(() => data.value?.items.slice(0, SHOWN) ?? [])

function isWorking(scan: ScanSummary) {
  return scan.status === 'pending' || scan.status === 'running'
}
</script>

<template>
  <aside
    aria-labelledby="recent-scans-heading"
    class="flex flex-col gap-3"
  >
    <div class="flex items-baseline justify-between">
      <h2
        id="recent-scans-heading"
        class="eyebrow text-muted"
      >
        Recent scans
      </h2>
      <ULink
        to="/history"
        class="text-sm font-medium text-primary"
      >
        All history →
      </ULink>
    </div>

    <ul
      v-if="scans.length"
      class="border-t border-inverted"
    >
      <li
        v-for="scan in scans"
        :key="scan.id"
        class="border-b border-default"
      >
        <NuxtLink
          :to="`/scan/${scan.id}`"
          class="grid grid-cols-[12px_minmax(0,1fr)_auto] items-center gap-3.5 px-1 py-4 transition-colors hover:bg-default/60"
        >
          <span
            v-if="isWorking(scan)"
            class="flex size-3 items-center justify-center"
          >
            <UIcon
              name="i-lucide-loader-circle"
              class="size-3 animate-spin text-muted"
            />
          </span>
          <span
            v-else-if="scan.status === 'error' || !scan.recommendation"
            class="size-2.5 rounded-full border-2 border-accented"
          />
          <span
            v-else
            class="size-2.5 rounded-xs"
            :class="RECOMMENDATION_CLASSES[scan.recommendation].dot"
          />

          <span class="flex min-w-0 flex-col gap-0.5">
            <span
              class="truncate text-[15px] font-medium text-highlighted"
              :title="scan.target"
            >{{ splitScanTitle(scan.target).name }}</span>
            <span
              class="truncate font-mono text-xs text-dimmed"
              :title="formatDate(scan.created_at)"
            >
              <template v-if="splitScanTitle(scan.target).source">{{ splitScanTitle(scan.target).source }} · </template>
              <NuxtTime
                :datetime="scan.created_at * 1000"
                relative
              />
            </span>
          </span>

          <span class="flex flex-col items-end gap-0.5 text-xs">
            <template v-if="isWorking(scan)">
              <span class="font-mono text-sm text-muted tabular-nums">{{ scan.completed_steps }}/{{ scan.total_steps }}</span>
              <span class="text-muted">{{ scan.status === 'pending' ? 'Queued' : 'Scanning' }}</span>
            </template>
            <template v-else-if="scan.status === 'error'">
              <span class="font-mono text-sm text-dimmed">—</span>
              <span class="text-critical-ink">Scan failed</span>
            </template>
            <template v-else-if="scan.recommendation">
              <span
                class="font-mono text-base font-medium tabular-nums"
                :class="RECOMMENDATION_CLASSES[scan.recommendation].ink"
              >{{ scan.risk_score }}</span>
              <span :class="RECOMMENDATION_CLASSES[scan.recommendation].ink">{{ RECOMMENDATION_SHORT_LABEL[scan.recommendation] }}</span>
            </template>
          </span>
        </NuxtLink>
      </li>
    </ul>

    <p
      v-else
      class="border-t border-inverted pt-4 text-sm text-muted"
    >
      Scans you run show up here, so you can come back to a result later.
    </p>
  </aside>
</template>
