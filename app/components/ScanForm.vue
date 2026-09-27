<script setup lang="ts">
import type { LLMConfig, LLMProvider } from '~~/shared/types/scan'
import type { ScanTargetKind } from '~~/shared/utils/scan'

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
const targetTouched = ref(false)
const targetInfo = computed(() => describeScanTarget(target.value))
const targetProblem = computed(() =>
  targetTouched.value && targetInfo.value && !targetInfo.value.ok ? targetInfo.value.problem : undefined
)

const TARGET_KIND_LABELS: Record<ScanTargetKind, { icon: string, label: string }> = {
  repository: { icon: 'i-lucide-git-branch', label: 'repository' },
  file: { icon: 'i-lucide-file-text', label: 'single file' },
  archive: { icon: 'i-lucide-file-archive', label: 'archive' }
}
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
const backendDown = computed(() => health.value?.status === 'down')
const canSubmit = computed(() => {
  if (backendDown.value) return false
  if (!targetInfo.value?.ok) return false
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
  targetTouched.value = true
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
    errorMessage.value = apiErrorMessage(err, 'Failed to start scan')
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
      <UAlert
        v-if="backendDown"
        color="warning"
        variant="subtle"
        icon="i-lucide-server-off"
        title="The scanner is unavailable right now"
        description="The scan service isn’t responding, so new scans can’t start. Past results in the history are still available."
      />

      <UFormField
        label="Skill source"
        description="A repository or a single SKILL.md file on GitHub, GitLab, Bitbucket or Hugging Face."
        :error="targetProblem"
      >
        <UInput
          v-model="target"
          type="url"
          inputmode="url"
          placeholder="https://github.com/org/repo"
          icon="i-lucide-link"
          class="w-full"
          :disabled="submitting"
          @blur="targetTouched = true"
        />
        <template #help>
          <span
            v-if="targetInfo?.ok"
            class="flex items-center gap-1.5 min-w-0"
          >
            <UIcon
              :name="TARGET_KIND_LABELS[targetInfo.kind].icon"
              class="size-4 shrink-0 text-primary"
            />
            <span class="shrink-0">{{ targetInfo.host }} {{ TARGET_KIND_LABELS[targetInfo.kind].label }}</span>
            <span class="text-highlighted font-medium truncate">{{ targetInfo.title }}</span>
          </span>
        </template>
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
        icon="i-lucide-circle-alert"
        title="Couldn’t start the scan"
        :description="errorMessage"
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
