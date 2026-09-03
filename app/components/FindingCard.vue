<script setup lang="ts">
import type { Finding } from '~~/shared/types/scan'

defineProps<{
  finding: Finding
}>()
</script>

<template>
  <UCard>
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
      <span class="font-semibold">Remediation:</span> {{ finding.remediation }}
    </p>

    <pre
      v-if="finding.code_snippet"
      class="mt-3 overflow-x-auto rounded-md bg-elevated p-3 text-xs font-mono"
    >{{ finding.code_snippet }}</pre>

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
