<script setup lang="ts">
import type { ScanReport, Severity } from '~~/shared/types/scan'

const props = defineProps<{
  report: ScanReport
}>()

const recommendation = computed(() => props.report.risk_assessment.recommendation)
const tone = computed(() => RECOMMENDATION_CLASSES[recommendation.value])
const score = computed(() => props.report.risk_assessment.score)
const severity = computed(() => props.report.risk_assessment.severity)

// The gauge: a 270° arc, open at the bottom, filled in proportion to the score.
const RADIUS = 52
const ARC = 2 * Math.PI * RADIUS * 0.75
const dashOffset = computed(() => ARC * (1 - Math.min(Math.max(score.value, 0), 100) / 100))

const counts = computed(() => {
  const result: Record<Severity, number> = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 }
  for (const issue of props.report.issues) result[issue.severity]++
  return SEVERITIES.map(level => ({ severity: level, count: result[level] })).filter(({ count }) => count > 0)
})

const topFinding = computed(() =>
  [...props.report.issues].sort((a, b) =>
    SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity] || b.confidence - a.confidence)[0]
)

const summary = computed(() => {
  const top = topFinding.value
  if (!top) return 'None of the analyzers flagged anything in this skill.'
  const title = findingTitle(top)
  const explanation = top.explanation?.trim()
  if (!explanation || explanation === title) return `Top finding: ${title}.`
  return `Top finding: ${title}. ${/[.!?]$/.test(explanation) ? explanation : `${explanation}.`}`
})
</script>

<template>
  <section
    aria-labelledby="verdict-heading"
    class="relative grid gap-8 overflow-hidden rounded-[2rem] border p-6 sm:p-10 lg:grid-cols-[minmax(0,1fr)_20rem] lg:gap-12 lg:px-12"
    :class="tone.panel"
  >
    <div class="flex min-w-0 flex-col gap-5">
      <p
        class="eyebrow flex items-center gap-2"
        :class="tone.ink"
      >
        <span
          class="size-1.5 rounded-full"
          :class="tone.dot"
        />
        Verdict
      </p>
      <h1
        id="verdict-heading"
        class="display flex items-center gap-3 text-5xl sm:gap-4 sm:text-7xl"
        :class="tone.ink"
      >
        <UIcon
          :name="RECOMMENDATION_ICON[recommendation]"
          class="size-10 shrink-0 sm:size-14"
        />
        {{ RECOMMENDATION_LABEL[recommendation] }}
      </h1>
      <p class="max-w-2xl text-base text-highlighted text-pretty sm:text-lg">
        {{ summary }}
      </p>
      <div class="mt-1 flex min-w-0 flex-col gap-1.5 rounded-2xl bg-default/60 p-4 ring-1 ring-default/60 backdrop-blur">
        <slot />
      </div>
    </div>

    <div class="flex flex-col items-center justify-center gap-6 rounded-[1.5rem] bg-default/70 p-6 ring-1 ring-default/60 backdrop-blur">
      <div
        role="meter"
        aria-label="Risk score"
        aria-valuemin="0"
        aria-valuemax="100"
        :aria-valuenow="score"
        class="relative size-44"
      >
        <svg
          viewBox="0 0 120 120"
          class="size-full rotate-135"
          aria-hidden="true"
        >
          <circle
            cx="60"
            cy="60"
            :r="RADIUS"
            fill="none"
            stroke-width="10"
            stroke-linecap="round"
            class="stroke-(--ui-bg-accented)"
            :stroke-dasharray="`${ARC} ${2 * Math.PI * RADIUS}`"
          />
          <circle
            cx="60"
            cy="60"
            :r="RADIUS"
            fill="none"
            stroke-width="10"
            stroke-linecap="round"
            class="transition-[stroke-dashoffset] duration-1000 ease-out"
            :class="SEVERITY_CLASSES[severity].stroke"
            :stroke-dasharray="`${ARC} ${2 * Math.PI * RADIUS}`"
            :stroke-dashoffset="dashOffset"
          />
        </svg>
        <div class="absolute inset-0 flex flex-col items-center justify-center">
          <span
            class="display text-6xl tabular-nums"
            :class="tone.ink"
          >{{ score }}</span>
          <span class="mt-1 font-mono text-xs text-muted">risk / 100</span>
        </div>
        <span class="absolute inset-x-0 bottom-1 text-center text-xs font-medium text-highlighted">
          {{ SEVERITY_LABEL[severity] }}
        </span>
      </div>

      <div class="flex w-full flex-col gap-2.5">
        <span class="text-sm font-semibold text-highlighted">
          {{ report.issues.length }} finding{{ report.issues.length === 1 ? '' : 's' }}
        </span>
        <template v-if="counts.length">
          <div
            aria-hidden="true"
            class="flex h-2 gap-1"
          >
            <span
              v-for="{ severity: level, count } in counts"
              :key="level"
              class="rounded-full"
              :class="SEVERITY_CLASSES[level].dot"
              :style="{ flexGrow: count }"
            />
          </div>
          <p class="flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted">
            <span
              v-for="{ severity: level, count } in counts"
              :key="level"
            ><b class="font-mono font-medium text-highlighted">{{ count }}</b> {{ SEVERITY_LABEL[level].toLowerCase() }}</span>
          </p>
        </template>
        <p
          v-else
          class="text-sm text-muted"
        >
          Nothing to review.
        </p>
      </div>
    </div>
  </section>
</template>
