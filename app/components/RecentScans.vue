<script setup lang="ts">
const SHOWN = 5

const { data } = useRecentScans()
const scans = computed(() => data.value?.items.slice(0, SHOWN) ?? [])
</script>

<template>
  <section
    v-if="scans.length"
    aria-labelledby="recent-scans-heading"
    class="flex flex-col gap-3"
  >
    <div class="flex items-center justify-between">
      <h2
        id="recent-scans-heading"
        class="text-sm font-semibold text-highlighted"
      >
        Recent scans
      </h2>
      <UButton
        to="/history"
        label="See all"
        trailing-icon="i-lucide-arrow-right"
        color="neutral"
        variant="link"
        size="xs"
      />
    </div>

    <UCard :ui="{ body: 'p-0 sm:p-0' }">
      <ul class="divide-y divide-default">
        <li
          v-for="scan in scans"
          :key="scan.id"
        >
          <NuxtLink
            :to="`/scan/${scan.id}`"
            class="flex items-center gap-3 px-4 py-3 hover:bg-elevated/50 transition-colors"
          >
            <div class="min-w-0 flex-1">
              <p class="text-sm font-medium truncate">
                {{ parseScanTarget(scan.target).title }}
              </p>
              <p
                :title="formatDate(scan.created_at)"
                class="text-xs text-muted"
              >
                <NuxtTime
                  :datetime="scan.created_at * 1000"
                  relative
                />
              </p>
            </div>

            <UBadge
              v-if="scan.status === 'pending' || scan.status === 'running'"
              color="neutral"
              variant="subtle"
              icon="i-lucide-loader-circle"
              :ui="{ leadingIcon: 'animate-spin' }"
            >
              {{ scan.status === 'pending' ? 'Queued' : 'Scanning' }}
            </UBadge>
            <UBadge
              v-else-if="scan.status === 'error'"
              color="error"
              variant="subtle"
              icon="i-lucide-x-circle"
            >
              Failed
            </UBadge>
            <UBadge
              v-else-if="scan.recommendation"
              :color="RECOMMENDATION_COLOR[scan.recommendation]"
              :icon="RECOMMENDATION_ICON[scan.recommendation]"
              variant="subtle"
            >
              {{ RECOMMENDATION_LABEL[scan.recommendation] }}
            </UBadge>
            <UIcon
              name="i-lucide-chevron-right"
              class="size-4 text-dimmed shrink-0"
            />
          </NuxtLink>
        </li>
      </ul>
    </UCard>
  </section>
</template>
