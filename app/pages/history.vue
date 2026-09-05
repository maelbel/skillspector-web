<script setup lang="ts">
useSeoMeta({ title: 'Scan history — Skillspector Web' })

const { data, status, error, hasMore, loadMore } = useScanHistory()

const RECOMMENDATION_COLOR: Record<string, 'success' | 'warning' | 'error'> = {
  SAFE: 'success',
  CAUTION: 'warning',
  DO_NOT_INSTALL: 'error'
}

function formatDate(seconds: number) {
  return new Date(seconds * 1000).toLocaleString()
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
          class="block"
        >
          <UCard class="hover:bg-elevated/50 transition-colors">
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
                  <p class="text-xs text-muted mt-1">
                    {{ formatDate(scan.created_at) }}
                  </p>
                </div>
              </div>

              <div class="flex items-center gap-3 shrink-0">
                <template v-if="scan.status === 'pending' || scan.status === 'running'">
                  <UIcon
                    name="i-lucide-loader-circle"
                    class="size-4 animate-spin text-primary"
                  />
                  <span class="text-sm text-muted capitalize">{{ scan.status }}</span>
                </template>
                <template v-else-if="scan.status === 'error'">
                  <UBadge
                    color="error"
                    variant="subtle"
                  >
                    Failed
                  </UBadge>
                </template>
                <template v-else>
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
  </UContainer>
</template>
