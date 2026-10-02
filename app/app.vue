<script setup lang="ts">
const { site } = useAppConfig()
const route = useRoute()

useHead({
  htmlAttrs: { lang: 'en' }
})

// Link previews (Slack, Discord, LinkedIn, X) need absolute URLs.
const siteUrl = useSiteUrl()
// Only the public pages are indexed (shared/utils/seo.ts); their canonical URL is on the configured
// address, so the production alias and a custom domain don't compete.
const siteUrlConfigured = !!useRuntimeConfig().public.siteUrl
const indexable = computed(() => isIndexable(route.path))
const canonical = computed(() => siteUrlConfigured && indexable.value ? `${siteUrl}${route.path}` : null)
useHead({
  link: () => canonical.value ? [{ rel: 'canonical', href: canonical.value }] : []
})
useSeoMeta({
  robots: () => indexable.value ? undefined : NOINDEX,
  title: site.name,
  description: site.description,
  ogTitle: site.name,
  ogDescription: site.description,
  ogType: 'website',
  ogSiteName: site.name,
  ogUrl: () => `${siteUrl}${route.path}`,
  ogImage: `${siteUrl}${site.ogImage.path}`,
  ogImageType: 'image/png',
  ogImageWidth: 1200,
  ogImageHeight: 630,
  ogImageAlt: site.ogImage.alt,
  twitterCard: 'summary_large_image'
})

const { accounts, user, isAdmin, signOut } = useAuth()
const { enabled: legalPages } = useLegal()
const legalLinks = [
  { to: '/legal', label: 'Legal notice' },
  { to: '/privacy', label: 'Privacy policy' },
  { to: '/terms', label: 'Terms of use' }
]
const colorMode = useColorMode()

// With accounts on, signed-out visitors only see the sign-in page, and only admins see Admin.
const signedIn = computed(() => !accounts.value || !!user.value)
const nav = computed(() => [
  { to: '/', label: 'Scan', icon: 'i-lucide-scan-search' },
  { to: '/history', label: 'History', icon: 'i-lucide-history' },
  ...(isAdmin.value ? [{ to: '/admin', label: 'Admin', icon: 'i-lucide-settings' }] : [])
])

// The Admin tab stays lit across the backoffice's sections.
function isCurrent(to: string) {
  return to === '/admin' ? route.path.startsWith('/admin') : route.path === to
}

const accountMenu = computed(() => [
  [{ label: user.value?.email ?? '', type: 'label' as const }],
  [
    // On phones the header has no room for the theme button, so it lives here.
    {
      label: colorMode.value === 'dark' ? 'Light theme' : 'Dark theme',
      icon: colorMode.value === 'dark' ? 'i-lucide-sun' : 'i-lucide-moon',
      class: 'sm:hidden',
      onSelect: () => {
        colorMode.preference = colorMode.value === 'dark' ? 'light' : 'dark'
      }
    },
    { label: 'Account', icon: 'i-lucide-user-round', to: '/account' },
    { label: 'Sign out', icon: 'i-lucide-log-out', onSelect: signOut }
  ]
])
</script>

<template>
  <UApp>
    <!-- Black in both themes, as on nvidia.com. -->
    <header class="sticky top-0 z-40 bg-black text-white">
      <UContainer class="flex h-(--ui-header-height) items-stretch justify-between gap-2 sm:gap-4">
        <NuxtLink
          to="/"
          class="flex min-w-0 items-center gap-2.5 sm:gap-3"
        >
          <span class="flex size-8 shrink-0 items-center justify-center bg-brand text-black">
            <UIcon
              name="i-lucide-scan-eye"
              class="size-5"
            />
          </span>
          <span class="text-base font-extrabold tracking-tight sm:text-lg">SKILLSPECTOR<span class="ml-1.5 font-medium text-graphite-400 max-sm:hidden">web</span></span>
        </NuxtLink>

        <nav
          aria-label="Main"
          class="flex items-stretch"
        >
          <NuxtLink
            v-for="item in signedIn ? nav : []"
            :key="item.to"
            :to="item.to"
            :aria-current="isCurrent(item.to) ? 'page' : undefined"
            class="relative flex min-w-10 items-center justify-center gap-2 px-2 text-sm font-bold transition-colors sm:min-w-11 sm:px-4"
            :class="isCurrent(item.to) ? 'text-white' : 'text-graphite-400 hover:text-white'"
          >
            <UIcon
              :name="item.icon"
              class="size-5 sm:hidden"
            />
            <span class="max-sm:sr-only">{{ item.label }}</span>
            <span
              v-if="isCurrent(item.to)"
              aria-hidden="true"
              class="absolute inset-x-2 bottom-0 h-[3px] bg-brand sm:inset-x-4"
            />
          </NuxtLink>

          <span class="flex items-center gap-0.5 sm:pl-2">
            <UColorModeButton
              color="neutral"
              variant="ghost"
              class="size-10 justify-center text-graphite-400 hover:bg-white/10 hover:text-white sm:size-11"
              :class="{ 'max-sm:hidden': user }"
            />
            <UDropdownMenu
              v-if="user"
              :items="accountMenu"
              :content="{ align: 'end' }"
            >
              <UButton
                icon="i-lucide-circle-user-round"
                color="neutral"
                variant="ghost"
                :aria-label="`Account: ${user.email}`"
                class="size-10 justify-center text-graphite-400 hover:bg-white/10 hover:text-white sm:size-11"
              />
            </UDropdownMenu>
            <UButton
              :to="`https://github.com/${site.repo}`"
              target="_blank"
              icon="i-simple-icons-github"
              aria-label="skillspector-web on GitHub"
              color="neutral"
              variant="ghost"
              class="size-11 justify-center text-graphite-400 hover:bg-white/10 hover:text-white max-sm:hidden"
            />
          </span>
        </nav>
      </UContainer>
    </header>

    <main class="min-h-[calc(100vh-var(--ui-header-height)-6rem)]">
      <NuxtPage />
    </main>

    <footer class="mt-12 bg-black text-graphite-400">
      <UContainer class="flex flex-col gap-1.5 py-8 text-sm">
        <p>
          Scans run on this server with <ULink
            :to="`https://github.com/${site.scannerRepo}`"
            target="_blank"
            class="font-semibold text-white underline underline-offset-2 hover:text-brand"
          >{{ site.scannerRepo }}</ULink>. Skill content reaches an AI provider only when you pick AI
          review for a scan.
        </p>
        <p class="text-xs text-graphite-500">
          An independent web UI for skillspector. Not affiliated with or endorsed by NVIDIA.
        </p>
        <nav
          v-if="legalPages"
          aria-label="Legal"
          class="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs"
        >
          <ULink
            v-for="link in legalLinks"
            :key="link.to"
            :to="link.to"
            class="text-graphite-400 underline-offset-2 hover:text-white hover:underline"
          >
            {{ link.label }}
          </ULink>
        </nav>
      </UContainer>
    </footer>
  </UApp>
</template>
