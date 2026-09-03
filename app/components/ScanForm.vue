<script setup lang="ts">
const { data: health } = await useFetch('/api/health')

const target = ref('')
const useLlm = ref(false)
const submitting = ref(false)
const errorMessage = ref('')

async function submit() {
  if (!target.value.trim()) return

  submitting.value = true
  errorMessage.value = ''

  try {
    const { id } = await $fetch<{ id: string }>('/api/scan', {
      method: 'POST',
      body: { target: target.value.trim(), useLlm: useLlm.value }
    })
    await navigateTo(`/scan/${id}`)
  } catch (err) {
    errorMessage.value = err instanceof Error ? err.message : 'Failed to start scan'
    submitting.value = false
  }
}
</script>

<template>
  <UCard>
    <form
      class="flex flex-col gap-4"
      @submit.prevent="submit"
    >
      <UFormField
        label="Skill source"
        description="A Git repo, zip, or file URL — e.g. https://github.com/some-org/some-skill"
      >
        <UInput
          v-model="target"
          placeholder="https://github.com/org/repo"
          icon="i-lucide-link"
          class="w-full"
          :disabled="submitting"
        />
      </UFormField>

      <UFormField v-if="health?.llm_available">
        <USwitch
          v-model="useLlm"
          label="Use LLM semantic analysis"
          description="Slower and uses API credits, but catches intent-based issues static rules miss."
          :disabled="submitting"
        />
      </UFormField>
      <p
        v-else
        class="text-xs text-muted"
      >
        LLM semantic analysis is unavailable (no provider configured on the server) — static
        analysis only.
      </p>

      <UAlert
        v-if="errorMessage"
        color="error"
        variant="subtle"
        :title="errorMessage"
      />

      <UButton
        type="submit"
        icon="i-lucide-scan-search"
        :loading="submitting"
        :disabled="!target.trim()"
        block
      >
        Scan
      </UButton>
    </form>
  </UCard>
</template>
