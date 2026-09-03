<script setup lang="ts">
import type { LLMConfig, LLMProvider } from '~~/shared/types/scan'

const PROVIDER_OPTIONS: { value: LLMProvider, label: string }[] = [
  { value: 'anthropic', label: 'Anthropic' },
  { value: 'openai', label: 'OpenAI' },
  { value: 'ollama', label: 'Ollama (self-hosted)' }
]

const target = ref('')
const useLlm = ref(false)
const provider = ref<LLMProvider>('anthropic')
const apiKey = ref('')
const baseUrl = ref('')
const model = ref('')
const submitting = ref(false)
const errorMessage = ref('')

const needsApiKey = computed(() => provider.value !== 'ollama')
const canSubmit = computed(() => {
  if (!target.value.trim()) return false
  if (useLlm.value && needsApiKey.value && !apiKey.value.trim()) return false
  return true
})

const baseUrlPlaceholder = computed(() => {
  switch (provider.value) {
    case 'ollama':
      return 'http://host.docker.internal:11434/v1'
    case 'openai':
      return 'https://api.openai.com/v1 (or an OpenAI-compatible endpoint)'
    default:
      return 'https://api.anthropic.com'
  }
})

async function submit() {
  if (!canSubmit.value) return

  submitting.value = true
  errorMessage.value = ''

  const llm: LLMConfig | undefined = useLlm.value
    ? {
        provider: provider.value,
        apiKey: apiKey.value.trim() || undefined,
        baseUrl: baseUrl.value.trim() || undefined,
        model: model.value.trim() || undefined
      }
    : undefined

  try {
    const { id } = await $fetch<{ id: string }>('/api/scan', {
      method: 'POST',
      body: { target: target.value.trim(), llm }
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

      <UFormField>
        <USwitch
          v-model="useLlm"
          label="Use LLM semantic analysis"
          description="Slower and uses your own API credits, but catches intent-based issues static rules miss."
          :disabled="submitting"
        />
      </UFormField>

      <div
        v-if="useLlm"
        class="flex flex-col gap-3 rounded-lg border border-default p-3"
      >
        <UFormField label="Provider">
          <USelect
            v-model="provider"
            :items="PROVIDER_OPTIONS"
            value-key="value"
            class="w-full"
            :disabled="submitting"
          />
        </UFormField>

        <UFormField
          v-if="needsApiKey"
          label="API key"
          description="Sent only for this scan, used to call the provider directly, never stored."
        >
          <UInput
            v-model="apiKey"
            type="password"
            placeholder="sk-..."
            class="w-full"
            :disabled="submitting"
          />
        </UFormField>

        <UFormField
          label="Base URL"
          description="Optional — override for a proxy or OpenAI-compatible endpoint."
        >
          <UInput
            v-model="baseUrl"
            :placeholder="baseUrlPlaceholder"
            class="w-full"
            :disabled="submitting"
          />
        </UFormField>

        <UFormField
          label="Model"
          description="Optional — defaults to the provider's recommended model."
        >
          <UInput
            v-model="model"
            placeholder="e.g. claude-opus-4-6"
            class="w-full"
            :disabled="submitting"
          />
        </UFormField>
      </div>

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
        :disabled="!canSubmit"
        block
      >
        Scan
      </UButton>
    </form>
  </UCard>
</template>
