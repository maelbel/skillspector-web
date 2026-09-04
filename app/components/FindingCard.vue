<script setup lang="ts">
import type { Finding, Severity } from '~~/shared/types/scan'

defineProps<{
  finding: Finding
}>()

const BORDER_COLOR: Record<Severity, string> = {
  CRITICAL: 'border-l-error',
  HIGH: 'border-l-error',
  MEDIUM: 'border-l-warning',
  LOW: 'border-l-primary'
}
</script>

<template>
  <UCard
    class="border-l-4"
    :class="BORDER_COLOR[finding.severity]"
  >
    <template #header>
      <div class="flex flex-wrap items-center justify-between gap-2">
        <div class="flex items-center gap-2">
          <SeverityBadge :severity="finding.severity" />
          <span
            v-if="finding.category"
            class="text-sm text-muted font-mono"
          >{{ finding.category }}</span>
        </div>
        <span class="text-xs text-muted font-mono">
          {{ finding.location.file }}:{{ finding.location.start_line }}
        </span>
      </div>
    </template>

    <p class="font-medium">
      {{ finding.explanation ?? finding.finding }}
    </p>

    <p
      v-if="finding.remediation"
      class="mt-2 text-sm text-muted"
    >
      <span class="font-semibold text-default">Remediation:</span> {{ finding.remediation }}
    </p>

    <div v-if="finding.code_snippet">
      <p class="mt-3 mb-1 text-xs font-semibold text-muted uppercase tracking-wide">
        Code
      </p>
      <pre class="overflow-x-auto rounded-md bg-elevated p-3 text-xs font-mono">{{ finding.code_snippet }}</pre>
    </div>

    <div
      v-if="finding.tags.length"
      class="mt-3 flex flex-wrap gap-1"
    >
      <UBadge
        v-for="tag in finding.tags"
        :key="tag"
        color="neutral"
        variant="subtle"
        size="sm"
      >
        {{ tag }}
      </UBadge>
    </div>
  </UCard>
</template>
