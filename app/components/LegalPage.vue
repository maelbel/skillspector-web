<script setup lang="ts">
// The frame of the legal notice, privacy policy and terms of use (app/pages/legal.vue, privacy.vue,
// terms.vue): not found until the operator sets their details (useLegal). In English, or in French
// with ?lang=fr; the default slot gets `fr` to pick its text.
const props = defineProps<{ title: string, lead: string, titleFr: string, leadFr: string }>()
defineSlots<{ default(props: { fr: boolean }): unknown }>()

const { legal, enabled } = useLegal()
if (!enabled) throw createError({ statusCode: 404, statusMessage: 'Page not found', fatal: true })

const route = useRoute()
const fr = computed(() => route.query.lang === 'fr')
const heading = computed(() => fr.value ? props.titleFr : props.title)

useHead({ htmlAttrs: { lang: () => fr.value ? 'fr' : 'en' } })
useSeoMeta({ title: () => `${heading.value} — Skillspector Web` })

const links = computed(() => [
  { path: '/legal', label: fr.value ? 'Mentions légales' : 'Legal notice' },
  { path: '/privacy', label: fr.value ? 'Politique de confidentialité' : 'Privacy policy' },
  { path: '/terms', label: fr.value ? 'Conditions d’utilisation' : 'Terms of use' }
])
const otherLanguage = computed(() => ({ path: route.path, query: fr.value ? {} : { lang: 'fr' } }))
</script>

<template>
  <UContainer class="py-12 sm:py-16">
    <article class="mx-auto flex max-w-3xl flex-col gap-8">
      <header class="flex flex-col gap-3">
        <div class="flex items-center justify-between gap-3">
          <p class="eyebrow text-brand-ink">
            {{ fr ? 'Informations légales' : 'Legal' }}
          </p>
          <UButton
            :to="otherLanguage"
            icon="i-lucide-languages"
            color="neutral"
            variant="outline"
            size="sm"
            :lang="fr ? 'en' : 'fr'"
          >
            {{ fr ? 'English' : 'Français' }}
          </UButton>
        </div>
        <h1 class="display text-4xl text-highlighted sm:text-5xl">
          {{ heading }}
        </h1>
        <p class="text-[15px] text-muted">
          {{ fr ? leadFr : lead }}
        </p>
        <p
          v-if="legal.updatedAt"
          class="text-sm text-muted"
        >
          {{ fr ? 'Dernière mise à jour :' : 'Last updated' }} <NuxtTime
            :datetime="legal.updatedAt"
            date-style="long"
            :locale="fr ? 'fr-FR' : 'en-GB'"
          />.
        </p>
      </header>

      <div class="legal-body flex flex-col gap-8 text-[15px] leading-relaxed text-default">
        <slot :fr="fr" />
      </div>

      <nav
        :aria-label="fr ? 'Informations légales' : 'Legal'"
        class="flex flex-wrap gap-x-4 gap-y-1 border-t border-default pt-6 text-sm"
      >
        <ULink
          v-for="link in links"
          :key="link.path"
          :to="{ path: link.path, query: fr ? { lang: 'fr' } : {} }"
          class="text-muted hover:text-highlighted"
        >
          {{ link.label }}
        </ULink>
      </nav>
    </article>
  </UContainer>
</template>

<style scoped>
.legal-body :deep(section) {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.legal-body :deep(h2) {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--ui-text-highlighted);
}

.legal-body :deep(h3) {
  font-weight: 600;
  color: var(--ui-text-highlighted);
}

.legal-body :deep(ul) {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  padding-left: 1.25rem;
  list-style: disc;
}

.legal-body :deep(a) {
  color: var(--ui-text-highlighted);
  text-decoration: underline;
  text-underline-offset: 2px;
}

.legal-body :deep(dl) {
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: 0.375rem 1.5rem;
}

.legal-body :deep(dt) {
  color: var(--ui-text-muted);
}

@media (max-width: 640px) {
  .legal-body :deep(dl) {
    grid-template-columns: 1fr;
    gap: 0 0;
  }

  .legal-body :deep(dd) {
    margin-bottom: 0.5rem;
  }
}
</style>
