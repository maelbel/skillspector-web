<script setup lang="ts">
import type { ScanSummary, Severity } from '~~/shared/types/scan'

useSeoMeta({ title: 'Scan history — Skillspector Web' })

const { data, status, error, refresh, hasMore, loadMore } = useScanHistory()

const RECOMMENDATION_COLOR: Record<string, 'success' | 'warning' | 'error'> = {
  SAFE: 'success',
  CAUTION: 'warning',
  DO_NOT_INSTALL: 'error'
}

const SEVERITY_BORDER: Record<Severity, string> = {
  CRITICAL: 'border-l-error',
  HIGH: 'border-l-error',
  MEDIUM: 'border-l-warning',
  LOW: 'border-l-primary'
}

const SEVERITY_TEXT: Record<Severity, string> = {
  CRITICAL: 'text-error',
  HIGH: 'text-error',
  MEDIUM: 'text-warning',
  LOW: 'text-primary'
}

function borderClass(scan: ScanSummary): string {
  if (scan.status === 'error') return 'border-l-error'
  if (scan.severity) return SEVERITY_BORDER[scan.severity]
  return 'border-l-default'
}

function formatDate(seconds: number) {
  return new Date(seconds * 1000).toLocaleString()
}

function formatRelativeTime(seconds: number): string {
  const diffSec = Math.round(Date.now() / 1000 - seconds)
  if (diffSec < 5) return 'just now'
  if (diffSec < 60) return `${diffSec}s ago`
  const diffMin = Math.round(diffSec / 60)
  if (diffMin < 60) return `${diffMin}m ago`
  const diffHour = Math.round(diffMin / 60)
  if (diffHour < 24) return `${diffHour}h ago`
  const diffDay = Math.round(diffHour / 24)
  if (diffDay < 30) return `${diffDay}d ago`
  return formatDate(seconds)
}

const deleteTarget = ref<ScanSummary | null>(null)
const deleting = ref(false)
const deleteError = ref('')

function openDeleteModal(scan: ScanSummary) {
  deleteTarget.value = scan
  deleteError.value = ''
}

function closeDeleteModal() {
  deleteTarget.value = null
}

async function confirmDelete() {
  if (!deleteTarget.value) return

  deleting.value = true
  deleteError.value = ''

  try {
    await $fetch(`/api/scan/${deleteTarget.value.id}`, { method: 'DELETE' })
    closeDeleteModal()
    await refresh()
  } catch (err) {
    deleteError.value = err instanceof Error ? err.message : 'Failed to delete scan'
  } finally {
    deleting.value = false
  }
}
</script>

<template>
  <UContainer class="py-16">
    <div class="max-w-3xl mx-auto flex flex-col gap-6">
      <div class="flex items-center justify-between">
        <h1 class="text-2xl font-bold tracking-tight">
          Scan history
        </h1>
        <UButton
          to="/"
          icon="i-lucide-plus"
          variant="soft"
          color="neutral"
        >
          New scan
        </UButton>
      </div>

      <UAlert
        v-if="error"
        color="error"
        variant="subtle"
        title="Failed to load scan history"
        :description="error.message"
      />

      <UCard v-else-if="status === 'pending'">
        <div class="flex items-center gap-3 py-2">
          <UIcon
            name="i-lucide-loader-circle"
            class="size-5 animate-spin text-primary"
          />
          <p class="text-sm text-muted">
            Loading scans…
          </p>
        </div>
      </UCard>

      <UAlert
        v-else-if="!data?.items.length"
        color="neutral"
        variant="subtle"
        icon="i-lucide-inbox"
        title="No scans yet"
        description="Scans you run will show up here."
      />

      <template v-else>
        <NuxtLink
          v-for="scan in data.items"
          :key="scan.id"
          :to="`/scan/${scan.id}`"
          class="block group"
        >
          <UCard
            class="hover:bg-elevated/50 transition-colors border-l-4"
            :class="borderClass(scan)"
          >
            <div class="flex items-center justify-between gap-4">
              <div class="min-w-0 flex items-center gap-2">
                <UIcon
                  v-if="parseScanTarget(scan.target).isGithub"
                  name="i-simple-icons-github"
                  class="size-4 text-muted shrink-0"
                />
                <div class="min-w-0">
                  <p class="text-sm font-medium truncate">
                    {{ parseScanTarget(scan.target).title }}
                  </p>
                  <p
                    v-if="scan.status === 'error' && scan.error"
                    class="text-xs text-error truncate mt-0.5"
                  >
                    {{ scan.error }}
                  </p>
                  <p
                    v-else-if="scan.status === 'running'"
                    class="text-xs text-muted mt-0.5"
                  >
                    Step {{ scan.completed_steps }} of {{ scan.total_steps }}
                  </p>
                  <p
                    v-else
                    :title="formatDate(scan.created_at)"
                    class="text-xs text-muted mt-0.5"
                  >
                    {{ formatRelativeTime(scan.created_at) }}
                  </p>
                </div>
              </div>

              <div class="flex items-center gap-3 shrink-0">
                <template v-if="scan.status === 'pending'">
                  <UIcon
                    name="i-lucide-loader-circle"
                    class="size-4 animate-spin text-muted"
                  />
                  <span class="text-sm text-muted">Queued</span>
                </template>
                <template v-else-if="scan.status === 'running'">
                  <UProgress
                    :model-value="scan.completed_steps"
                    :max="scan.total_steps"
                    size="sm"
                    class="w-16"
                  />
                </template>
                <template v-else-if="scan.status === 'error'">
                  <UBadge
                    color="error"
                    variant="subtle"
                    icon="i-lucide-x-circle"
                  >
                    Failed
                  </UBadge>
                </template>
                <template v-else>
                  <span
                    v-if="scan.risk_score !== null && scan.severity"
                    class="text-sm font-mono font-semibold tabular-nums"
                    :class="SEVERITY_TEXT[scan.severity]"
                  >
                    {{ scan.risk_score }}
                  </span>
                  <SeverityBadge
                    v-if="scan.severity"
                    :severity="scan.severity"
                  />
                  <UBadge
                    v-if="scan.recommendation"
                    :color="RECOMMENDATION_COLOR[scan.recommendation]"
                    variant="subtle"
                  >
                    {{ scan.recommendation }}
                  </UBadge>
                </template>
                <UButton
                  icon="i-lucide-trash-2"
                  variant="ghost"
                  color="neutral"
                  size="xs"
                  aria-label="Delete scan"
                  class="opacity-0 group-hover:opacity-100 focus-visible:opacity-100 transition-opacity"
                  @click.stop.prevent="openDeleteModal(scan)"
                />
                <UIcon
                  name="i-lucide-chevron-right"
                  class="size-4 text-muted"
                />
              </div>
            </div>
          </UCard>
        </NuxtLink>

        <UButton
          v-if="hasMore"
          variant="ghost"
          color="neutral"
          class="self-center"
          @click="loadMore"
        >
          Load more
        </UButton>
      </template>
    </div>

    <UModal
      :open="!!deleteTarget"
      title="Delete scan"
      description="This can't be undone."
      @update:open="(value) => { if (!value) closeDeleteModal() }"
    >
      <template #body>
        <div class="flex flex-col gap-4">
          <p class="text-sm text-muted font-mono break-all">
            {{ deleteTarget ? parseScanTarget(deleteTarget.target).title : '' }}
          </p>

          <UAlert
            v-if="deleteError"
            color="error"
            variant="subtle"
            :title="deleteError"
          />
        </div>
      </template>

      <template #footer>
        <div class="flex justify-end gap-2 w-full">
          <UButton
            variant="ghost"
            color="neutral"
            :disabled="deleting"
            @click="closeDeleteModal"
          >
            Cancel
          </UButton>
          <UButton
            color="error"
            icon="i-lucide-trash-2"
            :loading="deleting"
            @click="confirmDelete"
          >
            Delete
          </UButton>
        </div>
      </template>
    </UModal>
  </UContainer>
</template>
