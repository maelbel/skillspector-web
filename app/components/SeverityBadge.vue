<script setup lang="ts">
import type { Severity } from '~~/shared/types/scan'

const props = defineProps<{
  severity: Severity
  size?: 'sm' | 'md'
}>()

const COLORS: Record<Severity, 'error' | 'warning' | 'primary'> = {
  CRITICAL: 'error',
  HIGH: 'error',
  MEDIUM: 'warning',
  LOW: 'primary'
}

const color = computed(() => COLORS[props.severity])
</script>

<template>
  <UBadge
    :color="color"
    variant="subtle"
    :size="size ?? 'sm'"
  >
    <slot>{{ severity }}</slot>
  </UBadge>
</template>
