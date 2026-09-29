<script setup lang="ts">
const { site } = useAppConfig()
const route = useRoute()

useHead({
  htmlAttrs: { lang: 'en' }
})

useSeoMeta({
  title: site.name,
  description: site.description,
  ogTitle: site.name,
  ogDescription: site.description
})

const NAV = [
  { to: '/', label: 'Scan', icon: 'i-lucide-scan-search' },
  { to: '/history', label: 'History', icon: 'i-lucide-history' },
  { to: '/admin', label: 'Admin', icon: 'i-lucide-settings' }
]
</script>

<template>
  <UApp>
    <header class="sticky top-0 z-40 border-b border-default bg-ground/85 backdrop-blur">
      <UContainer class="flex h-(--ui-header-height) items-center justify-between gap-4">
        <NuxtLink
          to="/"
          class="flex items-center gap-2.5 text-highlighted"
        >
          <span class="flex size-8 items-center justify-center rounded-lg bg-inverted text-inverted">
            <UIcon
              name="i-lucide-shield-check"
              class="size-[18px]"
            />
          </span>
          <span class="font-serif text-[26px] leading-none">Skillspector</span>
        </NuxtLink>

        <nav
          aria-label="Main"
          class="flex items-center gap-1"
        >
          <NuxtLink
            v-for="item in NAV"
            :key="item.to"
            :to="item.to"
            :aria-current="route.path === item.to ? 'page' : undefined"
            class="flex h-11 min-w-11 items-center justify-center gap-2 rounded-lg px-3 text-sm font-medium transition-colors sm:px-4"
            :class="route.path === item.to ? 'bg-accented/70 text-highlighted' : 'text-muted hover:bg-elevated hover:text-highlighted'"
          >
            <UIcon
              :name="item.icon"
              class="size-5 sm:hidden"
            />
            <span class="max-sm:sr-only">{{ item.label }}</span>
          </NuxtLink>

          <span
            aria-hidden="true"
            class="mx-1 h-6 w-px bg-accented sm:mx-2"
          />

          <UColorModeButton
            color="neutral"
            variant="ghost"
            class="size-11 justify-center text-muted"
          />
          <UButton
            :to="`https://github.com/${site.repo}`"
            target="_blank"
            icon="i-simple-icons-github"
            aria-label="skillspector-web on GitHub"
            color="neutral"
            variant="ghost"
            class="size-11 justify-center text-muted max-sm:hidden"
          />
        </nav>
      </UContainer>
    </header>

    <main class="min-h-[calc(100vh-var(--ui-header-height)-4.5rem)]">
      <NuxtPage />
    </main>

    <footer class="border-t border-default">
      <UContainer class="py-6 text-sm text-muted">
        <p>
          Scans run on this server with <ULink
            :to="`https://github.com/${site.scannerRepo}`"
            target="_blank"
            class="font-medium text-highlighted underline underline-offset-2"
          >{{ site.scannerRepo }}</ULink>. Skill content reaches an AI provider only when you pick AI
          review for a scan.
        </p>
      </UContainer>
    </footer>
  </UApp>
</template>
