<script setup lang="ts">
import type { NuxtError } from '#app'

const props = defineProps<{
  error: NuxtError
}>()

const { site } = useAppConfig()

const statusCode = computed(() => props.error?.statusCode ?? 500)
const isNotFound = computed(() => statusCode.value === 404)
const message = computed(() => {
  if (isNotFound.value) return 'This page does not exist.'
  return props.error?.statusMessage || props.error?.message || 'Something went wrong.'
})

useSeoMeta({ title: `${statusCode.value} — ${site.name}` })

function goHome() {
  clearError({ redirect: '/' })
}
</script>

<template>
  <UApp>
    <UContainer class="py-24">
      <div class="max-w-lg mx-auto flex flex-col items-center text-center gap-4">
        <div class="flex items-center justify-center size-14 rounded-full bg-error/10">
          <UIcon
            :name="isNotFound ? 'i-lucide-file-question' : 'i-lucide-shield-alert'"
            class="size-7 text-error"
          />
        </div>
        <div>
          <h1 class="text-3xl font-bold tracking-tight">
            {{ statusCode }}
          </h1>
          <p class="mt-2 text-muted">
            {{ message }}
          </p>
        </div>
        <UButton
          icon="i-lucide-arrow-left"
          variant="soft"
          color="neutral"
          @click="goHome"
        >
          Back home
        </UButton>
      </div>
    </UContainer>
  </UApp>
</template>
