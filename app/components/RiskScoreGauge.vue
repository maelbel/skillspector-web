<script setup lang="ts">
import type { Recommendation, Severity } from '~~/shared/types/scan'

const props = defineProps<{
  score: number
  severity: Severity
  recommendation: Recommendation
}>()

const COLORS: Record<Severity, 'error' | 'warning' | 'primary'> = {
  CRITICAL: 'error',
  HIGH: 'error',
  MEDIUM: 'warning',
  LOW: 'primary'
}

const RING_STROKE: Record<Severity, string> = {
  CRITICAL: 'stroke-error',
  HIGH: 'stroke-error',
  MEDIUM: 'stroke-warning',
  LOW: 'stroke-primary'
}

const RECOMMENDATION_LABEL: Record<Recommendation, string> = {
  SAFE: 'Safe to install',
  CAUTION: 'Review before installing',
  DO_NOT_INSTALL: 'Do not install'
}

const RECOMMENDATION_ICON: Record<Recommendation, string> = {
  SAFE: 'i-lucide-check-circle-2',
  CAUTION: 'i-lucide-alert-triangle',
  DO_NOT_INSTALL: 'i-lucide-shield-x'
}

const color = computed(() => COLORS[props.severity])

const RADIUS = 42
const CIRCUMFERENCE = 2 * Math.PI * RADIUS
const dashOffset = computed(() => CIRCUMFERENCE * (1 - Math.min(Math.max(props.score, 0), 100) / 100))
</script>

<template>
  <UCard>
    <div class="flex items-center gap-6">
      <div class="relative flex items-center justify-center size-24 shrink-0">
        <svg
          viewBox="0 0 100 100"
          class="size-24 -rotate-90"
        >
          <circle
            cx="50"
            cy="50"
            :r="RADIUS"
            fill="none"
            stroke-width="8"
            class="stroke-default"
          />
          <circle
            cx="50"
            cy="50"
            :r="RADIUS"
            fill="none"
            stroke-width="8"
            stroke-linecap="round"
            :stroke-dasharray="CIRCUMFERENCE"
            :stroke-dashoffset="dashOffset"
            class="transition-[stroke-dashoffset] duration-700 ease-out"
            :class="RING_STROKE[severity]"
          />
        </svg>
        <span
          class="absolute text-2xl font-bold"
          :class="{
            'text-error': color === 'error',
            'text-warning': color === 'warning',
            'text-primary': color === 'primary'
          }"
        >{{ score }}</span>
      </div>

      <div>
        <p class="text-sm text-muted">
          Risk score
        </p>
        <p class="text-lg font-semibold">
          {{ severity }}
        </p>
        <p
          class="flex items-center gap-1.5 text-sm mt-1"
          :class="{
            'text-error': color === 'error',
            'text-warning': color === 'warning',
            'text-primary': color === 'primary'
          }"
        >
          <UIcon
            :name="RECOMMENDATION_ICON[recommendation]"
            class="size-4 shrink-0"
          />
          {{ RECOMMENDATION_LABEL[recommendation] }}
        </p>
      </div>
    </div>
  </UCard>
</template>
