<script setup lang="ts">
import type { LLMConfig, LLMProvider } from '~~/shared/types/scan'

const { data: health, pending: healthPending } = useFetch('/api/health')

const PROVIDER_LABELS: Record<LLMProvider, string> = {
  anthropic: 'Anthropic',
  openai: 'OpenAI',
  ollama: 'Ollama (self-hosted)',
  claude_cli: 'Claude CLI (server login)'
}

const PROVIDER_ICONS: Record<LLMProvider, string> = {
  anthropic: 'i-simple-icons-anthropic',
  openai: 'i-simple-icons-openai',
  ollama: 'i-simple-icons-ollama',
  claude_cli: 'i-lucide-terminal'
}

const providerOptions = computed(() => {
  const claudeCliLabel = healthPending.value
    ? 'Claude CLI (checking availability…)'
    : PROVIDER_LABELS.claude_cli

  return [
    { value: 'anthropic', label: PROVIDER_LABELS.anthropic, icon: PROVIDER_ICONS.anthropic },
    { value: 'openai', label: PROVIDER_LABELS.openai, icon: PROVIDER_ICONS.openai },
    { value: 'ollama', label: PROVIDER_LABELS.ollama, icon: PROVIDER_ICONS.ollama },
    { value: 'claude_cli', label: claudeCliLabel, icon: PROVIDER_ICONS.claude_cli, disabled: healthPending.value }
  ] satisfies { value: LLMProvider, label: string, icon: string, disabled?: boolean }[]
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
const claudeCliUnauthenticated = computed(() =>
  provider.value === 'claude_cli' && !healthPending.value && !health.value?.claude_cli_available
)
const canSubmit = computed(() => {
  if (!target.value.trim()) return false
  if (useLlm.value && needsApiKey.value && !apiKey.value.trim()) return false
  if (useLlm.value && claudeCliUnauthenticated.value) return false
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

      <Transition
        enter-active-class="transition duration-200 ease-out"
        enter-from-class="opacity-0 -translate-y-1"
        enter-to-class="opacity-100 translate-y-0"
        leave-active-class="transition duration-150 ease-in"
        leave-from-class="opacity-100 translate-y-0"
        leave-to-class="opacity-0 -translate-y-1"
      >
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

          <UAlert
            v-if="claudeCliUnauthenticated"
            color="warning"
            variant="subtle"
            icon="i-lucide-alert-triangle"
            title="Server not logged in"
            description="This server's Claude CLI hasn't been authenticated yet — an admin needs to complete the login before this provider will work."
          />

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
      </Transition>

      <UAlert
        v-if="errorMessage"
        color="error"
        variant="subtle"
        :title="errorMessage"
      />

      <UButton
        type="submit"
        icon="i-lucide-scan-search"
        size="lg"
        :loading="submitting"
        :disabled="!canSubmit"
        block
      >
        Scan
      </UButton>
    </form>
  </UCard>
</template>
