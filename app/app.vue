<script setup lang="ts">
const { site } = useAppConfig()

useHead({
  htmlAttrs: { lang: 'en' }
})

useSeoMeta({
  title: site.name,
  description: site.description,
  ogTitle: site.name,
  ogDescription: site.description
})
</script>

<template>
  <UApp>
    <UHeader :ui="{ root: 'border-b border-default backdrop-blur bg-default/80' }">
      <template #left>
        <NuxtLink
          to="/"
          class="flex items-center gap-2 font-semibold"
        >
          <UIcon
            name="i-lucide-shield-check"
            class="size-5 text-primary"
          />
          {{ site.name }}
        </NuxtLink>
      </template>

      <template #right>
        <UTooltip text="Toggle theme">
          <UColorModeButton />
        </UTooltip>
        <UButton
          :to="`https://github.com/${site.repo}`"
          target="_blank"
          icon="i-simple-icons-github"
          aria-label="skillspector on GitHub"
          color="neutral"
          variant="ghost"
        />
      </template>
    </UHeader>

    <UMain>
      <NuxtPage />
    </UMain>

    <UFooter>
      <template #left>
        <p class="text-sm text-muted">
          Runs <a
            :href="`https://github.com/${site.repo}`"
            target="_blank"
            class="underline"
          >{{ site.repo }}</a>'s own scan pipeline — nothing scanned here leaves this server.
        </p>
      </template>
    </UFooter>
  </UApp>
</template>
