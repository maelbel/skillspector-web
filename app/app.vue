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
    <header class="sticky top-3 z-40 px-3 sm:top-4 sm:px-4">
      <div class="mx-auto flex h-14 max-w-(--ui-container) items-center justify-between gap-3 rounded-full border border-default/70 bg-default/70 py-1.5 pr-1.5 pl-2 shadow-[0_8px_30px_-12px_rgb(27_31_26/0.18)] backdrop-blur-xl backdrop-saturate-150">
        <NuxtLink
          to="/"
          class="flex items-center gap-2.5 rounded-full py-1 pr-3 pl-1 text-highlighted"
        >
          <span class="relative flex size-9 items-center justify-center overflow-hidden rounded-full bg-matcha-500 text-white shadow-inner">
            <UIcon
              name="i-lucide-scan-eye"
              class="size-[18px]"
            />
          </span>
          <span class="text-[17px] font-semibold tracking-[-0.03em]">skillspector</span>
        </NuxtLink>

        <nav
          aria-label="Main"
          class="flex items-center gap-0.5"
        >
          <NuxtLink
            v-for="item in NAV"
            :key="item.to"
            :to="item.to"
            :aria-current="route.path === item.to ? 'page' : undefined"
            class="flex h-11 min-w-11 items-center justify-center gap-2 rounded-full px-3 text-sm font-medium transition-colors sm:px-4"
            :class="route.path === item.to ? 'bg-inverted text-inverted' : 'text-muted hover:bg-elevated hover:text-highlighted'"
          >
            <UIcon
              :name="item.icon"
              class="size-5 sm:hidden"
            />
            <span class="max-sm:sr-only">{{ item.label }}</span>
          </NuxtLink>

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
      </div>
    </header>

    <main class="min-h-[calc(100vh-10rem)]">
      <NuxtPage />
    </main>

    <footer class="mt-8 border-t border-default/70">
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
