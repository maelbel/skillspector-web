<script setup lang="ts">
// The backoffice shell: a sidebar next to whichever section is open (pages/admin/*).
const route = useRoute()
const { accounts } = useAuth()

const sections = computed(() => [
  { to: '/admin', label: 'Overview', icon: 'i-lucide-layout-dashboard', exact: true },
  ...(accounts.value ? [{ to: '/admin/users', label: 'Users', icon: 'i-lucide-users', exact: false }] : []),
  { to: '/admin/activity', label: 'Activity', icon: 'i-lucide-scroll-text', exact: true },
  { to: '/admin/settings', label: 'Settings', icon: 'i-lucide-settings', exact: true }
])

function isActive(section: { to: string, exact: boolean }) {
  return section.exact ? route.path === section.to : route.path.startsWith(section.to)
}
</script>

<template>
  <UContainer class="py-8 sm:py-10">
    <div class="grid gap-8 lg:grid-cols-[13rem_minmax(0,1fr)] lg:gap-10">
      <nav
        aria-label="Backoffice"
        class="flex min-w-0 flex-col gap-3 lg:sticky lg:top-[calc(var(--ui-header-height)+2rem)] lg:self-start"
      >
        <p class="eyebrow text-muted">
          Backoffice
        </p>
        <ul class="flex gap-1 overflow-x-auto lg:flex-col">
          <li
            v-for="section in sections"
            :key="section.to"
          >
            <NuxtLink
              :to="section.to"
              :aria-current="isActive(section) ? 'page' : undefined"
              class="flex h-11 items-center gap-2.5 border-l-[3px] px-3 text-sm font-semibold whitespace-nowrap transition-colors"
              :class="isActive(section) ? 'border-brand bg-default text-highlighted' : 'border-transparent text-muted hover:bg-default/60 hover:text-highlighted'"
            >
              <UIcon
                :name="section.icon"
                class="size-4 shrink-0"
              />
              {{ section.label }}
            </NuxtLink>
          </li>
        </ul>
      </nav>

      <div class="min-w-0">
        <NuxtPage />
      </div>
    </div>
  </UContainer>
</template>
