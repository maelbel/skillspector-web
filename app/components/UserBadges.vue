<script setup lang="ts">
import type { UserRole, UserStatus } from '~~/shared/types/auth'

defineProps<{
  role: UserRole
  status: UserStatus
}>()
</script>

<template>
  <span class="inline-flex flex-wrap gap-1.5">
    <span
      class="px-2 py-0.5 font-mono text-[11px] font-semibold tracking-wider uppercase"
      :class="role === 'admin' ? 'bg-black text-brand' : 'bg-elevated text-muted'"
    >{{ role }}</span>
    <span
      v-if="status === 'suspended'"
      class="bg-critical-tint px-2 py-0.5 font-mono text-[11px] font-semibold tracking-wider text-critical-ink uppercase ring-1 ring-critical-line"
    >suspended</span>
  </span>
</template>
