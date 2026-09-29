<script setup lang="ts">
import type { ScanReport, Severity } from '~~/shared/types/scan'

const props = defineProps<{
  report: ScanReport
}>()

const recommendation = computed(() => props.report.risk_assessment.recommendation)
const tone = computed(() => RECOMMENDATION_CLASSES[recommendation.value])
const score = computed(() => props.report.risk_assessment.score)

const counts = computed(() => {
  const result: Record<Severity, number> = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 }
  for (const issue of props.report.issues) result[issue.severity]++
  return SEVERITIES.map(severity => ({ severity, count: result[severity] })).filter(({ count }) => count > 0)
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
    class="grid gap-8 rounded-3xl border p-6 sm:p-10 lg:grid-cols-[minmax(0,1fr)_22rem] lg:gap-14 lg:px-12"
    :class="tone.panel"
  >
    <div class="flex min-w-0 flex-col gap-4">
      <p
        class="eyebrow"
        :class="tone.ink"
      >
        Verdict
      </p>
      <h1
        id="verdict-heading"
        class="flex items-center gap-3 font-serif text-5xl leading-none sm:gap-4 sm:text-7xl"
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
      <div
        class="flex min-w-0 flex-col gap-1.5 border-t pt-4"
        :class="tone.rule"
      >
        <slot />
      </div>
    </div>

    <div class="flex flex-col justify-center gap-6">
      <div class="flex flex-col gap-2.5">
        <div class="flex items-baseline justify-between">
          <span class="text-sm font-semibold text-highlighted">Risk score</span>
          <span
            class="font-mono"
            :class="tone.ink"
          >
            <span class="text-5xl leading-none font-medium tabular-nums sm:text-6xl">{{ score }}</span>
            <span class="text-lg text-muted"> / 100</span>
          </span>
        </div>
        <div
          role="meter"
          aria-label="Risk score"
          aria-valuemin="0"
          aria-valuemax="100"
          :aria-valuenow="score"
          class="h-2.5 overflow-hidden rounded-full bg-default/70"
        >
          <div
            class="h-full rounded-full transition-[width] duration-700 ease-out"
            :class="SEVERITY_CLASSES[report.risk_assessment.severity].dot"
            :style="{ width: `${Math.max(score, 2)}%` }"
          />
        </div>
        <p class="text-xs text-muted">
          Overall severity: <span class="font-medium text-highlighted">{{ SEVERITY_LABEL[report.risk_assessment.severity] }}</span>
        </p>
      </div>

      <div class="flex flex-col gap-2.5">
        <span class="text-sm font-semibold text-highlighted">
          {{ report.issues.length }} finding{{ report.issues.length === 1 ? '' : 's' }}
        </span>
        <template v-if="counts.length">
          <div
            aria-hidden="true"
            class="flex h-2.5 gap-0.5 overflow-hidden rounded-full"
          >
            <span
              v-for="{ severity, count } in counts"
              :key="severity"
              :class="SEVERITY_CLASSES[severity].dot"
              :style="{ flexGrow: count }"
            />
          </div>
          <p class="flex flex-wrap gap-x-4 gap-y-1 text-sm text-highlighted">
            <span
              v-for="{ severity, count } in counts"
              :key="severity"
            ><b class="font-mono font-medium">{{ count }}</b> {{ SEVERITY_LABEL[severity].toLowerCase() }}</span>
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
