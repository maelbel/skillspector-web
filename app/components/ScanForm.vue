<script setup lang="ts">
import type { LLMConfig, LLMProvider } from '~~/shared/types/scan'

const { data: health, pending: healthPending } = useFetch('/api/health')

const PROVIDER_LABELS: Record<LLMProvider, string> = {
  anthropic: 'Anthropic',
  openai: 'OpenAI',
  ollama: 'Ollama (self-hosted)',
  claude_cli: 'Claude CLI (server login)'
}

const providerOptions = computed(() => {
  const options: { value: LLMProvider, label: string, disabled?: boolean }[] = [
    { value: 'anthropic', label: PROVIDER_LABELS.anthropic },
    { value: 'openai', label: PROVIDER_LABELS.openai },
    { value: 'ollama', label: PROVIDER_LABELS.ollama }
  ]

  if (healthPending.value) {
    options.push({ value: 'claude_cli', label: 'Claude CLI (checking availability…)', disabled: true })
  } else if (health.value?.claude_cli_available) {
    options.push({ value: 'claude_cli', label: PROVIDER_LABELS.claude_cli })
  }

  return options
})

const target = ref('')
const useLlm = ref(false)
const provider = ref<LLMProvider>('anthropic')
const apiKey = ref('')
const baseUrl = ref('')
const model = ref('')
const submitting = ref(false)
const errorMessage = ref('')

const needsApiKey = computed(() => provider.value !== 'ollama' && provider.value !== 'claude_cli')
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

watch(provider, (value) => {
  if (value === 'claude_cli' && !health.value?.claude_cli_available) {
    provider.value = 'anthropic'
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
            :items="providerOptions"
            value-key="value"
            class="w-full"
            :disabled="submitting"
            :loading="healthPending"
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
        <p
          v-else-if="provider === 'claude_cli'"
          class="text-xs text-muted"
        >
          Uses this server's own Claude Code login — no key needed.
        </p>

        <UFormField
          v-if="provider !== 'claude_cli'"
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
