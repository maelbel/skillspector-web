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

const RECOMMENDATION_LABEL: Record<Recommendation, string> = {
  SAFE: 'Safe to install',
  CAUTION: 'Review before installing',
  DO_NOT_INSTALL: 'Do not install'
}

const color = computed(() => COLORS[props.severity])
</script>

<template>
  <UCard>
    <div class="flex items-center gap-6">
      <div
        class="relative flex items-center justify-center size-24 rounded-full border-4 shrink-0"
        :class="{
          'border-error text-error': color === 'error',
          'border-warning text-warning': color === 'warning',
          'border-primary text-primary': color === 'primary'
        }"
      >
        <span class="text-2xl font-bold">{{ score }}</span>
      </div>

      <div>
        <p class="text-sm text-muted">
          Risk score
        </p>
        <p
          class="text-lg font-semibold"
          :class="{
            'text-error': color === 'error',
            'text-warning': color === 'warning',
            'text-primary': color === 'primary'
          }"
        >
          {{ severity }} · {{ RECOMMENDATION_LABEL[recommendation] }}
        </p>
      </div>
    </div>
  </UCard>
</template>
