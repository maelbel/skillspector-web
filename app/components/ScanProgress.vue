<script setup lang="ts">
import type { ScanStatus } from '~~/shared/types/scan'

const props = defineProps<{
  status: ScanStatus | null | undefined
  title: string
  lines: string[]
}>()

const stages = computed(() => groupCompletedStages(props.lines))
const completed = computed(() => props.status?.completed_steps ?? 0)
const total = computed(() => props.status?.total_steps ?? 0)
const remaining = computed(() => Math.max(0, total.value - completed.value))
const queued = computed(() => props.status?.status === 'pending')
</script>

<template>
  <div class="flex flex-col gap-8">
    <div class="flex min-w-0 flex-col gap-3">
      <p class="eyebrow flex items-center gap-2.5 text-primary">
        <UIcon
          name="i-lucide-loader-circle"
          class="size-3.5 animate-spin"
        />
        {{ queued ? 'Queued' : 'Scanning' }}
      </p>
      <h1 class="font-serif text-4xl leading-tight break-words text-highlighted sm:text-6xl">
        {{ title }}
      </h1>
      <p
        v-if="status"
        class="font-mono text-sm break-all text-muted"
      >
        {{ status.target }}
      </p>
    </div>

    <div class="flex flex-col gap-2.5">
      <div class="flex flex-wrap justify-between gap-x-4 gap-y-1 text-sm">
        <span class="font-medium text-highlighted">
          <template v-if="total">Step {{ completed }} of {{ total }}</template>
          <template v-else>Starting…</template>
        </span>
        <span class="text-muted">Static scans usually take about a minute; with AI review, a few.</span>
      </div>
      <UProgress
        :model-value="completed"
        :max="total || 1"
        color="neutral"
        :ui="{ base: 'bg-accented' }"
      />
    </div>

    <div class="grid gap-6 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-8">
      <section
        aria-labelledby="stages-heading"
        class="flex flex-col rounded-2xl border border-default bg-default p-6"
      >
        <h2
          id="stages-heading"
          class="eyebrow mb-3 text-muted"
        >
          Analyzers
        </h2>
        <ul class="flex flex-col">
          <li
            v-for="stage in stages"
            :key="stage.label"
            class="flex items-center gap-3 border-b border-muted py-3"
          >
            <UIcon
              name="i-lucide-circle-check"
              class="size-[18px] shrink-0 text-primary"
            />
            <span class="flex-1 text-[15px] text-highlighted">{{ stage.label }}</span>
            <span class="font-mono text-sm text-muted tabular-nums">{{ stage.completed }} done</span>
          </li>
          <li class="-mx-3 mt-1 flex items-center gap-3 rounded-lg bg-ground px-3 py-3">
            <UIcon
              name="i-lucide-loader-circle"
              class="size-[18px] shrink-0 animate-spin text-highlighted"
            />
            <span class="flex-1 text-[15px] font-semibold text-highlighted">
              {{ queued ? 'Waiting for a free scan slot' : 'Running the next analyzers' }}
            </span>
            <span
              v-if="total && !queued"
              class="font-mono text-sm text-highlighted tabular-nums"
            >{{ remaining }} left</span>
          </li>
        </ul>
        <p class="mt-auto pt-5 text-sm text-muted">
          You can leave this page. The scan keeps running and its result shows up in History.
        </p>
      </section>

      <section
        aria-labelledby="log-heading"
        class="flex flex-col gap-3 rounded-2xl bg-code p-5 sm:p-6"
      >
        <div class="flex items-center justify-between">
          <h2
            id="log-heading"
            class="eyebrow text-bone-400"
          >
            Live log
          </h2>
          <span class="flex items-center gap-1.5 font-mono text-xs text-forest-300">
            <span class="size-1.5 animate-pulse rounded-full bg-forest-300" />
            streaming
          </span>
        </div>
        <ScanLogPanel
          v-if="lines.length"
          :lines="lines"
          tall
          class="-mx-4 -mb-4"
        />
        <p
          v-else
          class="font-mono text-xs text-bone-400"
        >
          Waiting for the first log line…
        </p>
      </section>
    </div>
  </div>
</template>
