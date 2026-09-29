<script setup lang="ts">
import type { LLMConfig, LLMProvider } from '~~/shared/types/scan'
import type { ScanTargetKind } from '~~/shared/utils/scan'

// Awaited so the server-rendered default provider matches the client's (see the watch below).
const { data: health, pending: healthPending } = await useFetch('/api/health')

const PROVIDER_LABELS: Record<LLMProvider, string> = {
  anthropic: 'Anthropic',
  openai: 'OpenAI',
  ollama: 'Ollama (self-hosted)',
  claude_cli: 'Claude via this server — no key needed'
}

const PROVIDER_RECIPIENTS: Record<LLMProvider, string> = {
  anthropic: 'Anthropic',
  openai: 'OpenAI (or the endpoint you set)',
  ollama: 'your Ollama server',
  claude_cli: 'Anthropic, through this server’s Claude login'
}

const API_KEY_LINKS: Partial<Record<LLMProvider, string>> = {
  anthropic: 'https://console.anthropic.com/settings/keys',
  openai: 'https://platform.openai.com/api-keys'
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

  type ProviderOption = { value: LLMProvider, label: string, icon: string, disabled?: boolean }
  const claudeCli: ProviderOption = { value: 'claude_cli', label: claudeCliLabel, icon: PROVIDER_ICONS.claude_cli, disabled: healthPending.value }
  const withKey: ProviderOption[] = [
    { value: 'anthropic', label: PROVIDER_LABELS.anthropic, icon: PROVIDER_ICONS.anthropic },
    { value: 'openai', label: PROVIDER_LABELS.openai, icon: PROVIDER_ICONS.openai },
    { value: 'ollama', label: PROVIDER_LABELS.ollama, icon: PROVIDER_ICONS.ollama }
  ]
  // The zero-setup option goes first when it works.
  return health.value?.claude_cli_available ? [claudeCli, ...withKey] : [...withKey, claudeCli]
})

// `/?target=…&deep=1` prefills the form, e.g. from a result page's "Scan again".
const route = useRoute()
const queryTarget = typeof route.query.target === 'string' ? route.query.target : ''
const target = ref(queryTarget)
const targetInput = useTemplateRef('targetInput')
const targetTouched = ref(!!queryTarget)
const targetInfo = computed(() => describeScanTarget(target.value))
const targetProblem = computed(() =>
  targetTouched.value && targetInfo.value && !targetInfo.value.ok ? targetInfo.value.problem : undefined
)

// Point at an existing result before starting a duplicate scan of the same URL.
const { data: recentScans } = useRecentScans()
const normalizeTarget = (value: string) => value.trim().replace(/\/+$/, '')
const previousScan = computed(() => {
  if (!targetInfo.value?.ok) return undefined
  const wanted = normalizeTarget(target.value)
  return recentScans.value?.items.find(scan => scan.status !== 'error' && normalizeTarget(scan.target) === wanted)
})

// Real, stable URLs: a published skill, and a skillspector test fixture that's flagged
// DO_NOT_INSTALL even without AI analysis.
const EXAMPLES = [
  { label: 'Anthropic’s PDF skill', icon: 'i-lucide-file-text', target: 'https://github.com/anthropics/skills/blob/main/skills/pdf/SKILL.md' },
  { label: 'A poisoned MCP tool', icon: 'i-lucide-skull', target: 'https://github.com/NVIDIA/skillspector/blob/main/tests/fixtures/mcp_poisoned_tool/SKILL.md' }
]

function useExample(example: typeof EXAMPLES[number]) {
  target.value = example.target
  targetTouched.value = true
  // The clicked chip disappears once the field is filled; keep focus in the form so Enter scans.
  targetInput.value?.inputRef?.focus()
}

const TARGET_KIND_LABELS: Record<ScanTargetKind, { icon: string, label: string }> = {
  repository: { icon: 'i-lucide-git-branch', label: 'repository' },
  file: { icon: 'i-lucide-file-text', label: 'single file' },
  archive: { icon: 'i-lucide-file-archive', label: 'archive' }
}

const useLlm = ref(false)
const depth = computed({
  get: () => useLlm.value ? 'ai' : 'static',
  set: (value: string) => {
    useLlm.value = value === 'ai'
  }
})
const provider = ref<LLMProvider>('anthropic')
const apiKey = ref('')
const baseUrl = ref('')
const model = ref('')
const advancedOpen = ref(false)
const submitting = ref(false)
const errorMessage = ref('')

// Remembered per browser so repeat visitors don't re-pick their setup. The API key never is.
const PREFS_KEY = 'skillspector:scan-prefs'
interface ScanPrefs {
  useLlm?: boolean
  provider?: LLMProvider
  baseUrl?: string
  model?: string
}
const hasStoredProvider = ref(false)

onMounted(() => {
  // Skip on touch devices, where focusing pops up the keyboard over the page.
  if (window.matchMedia('(pointer: fine)').matches) targetInput.value?.inputRef?.focus()

  let prefs: ScanPrefs = {}
  try {
    prefs = JSON.parse(localStorage.getItem(PREFS_KEY) ?? '{}') as ScanPrefs
  } catch {
    // Unreadable or unavailable storage: start from the defaults.
  }
  if (route.query.deep === '1') useLlm.value = true
  else if (typeof prefs.useLlm === 'boolean') useLlm.value = prefs.useLlm
  if (prefs.provider && prefs.provider in PROVIDER_LABELS) {
    provider.value = prefs.provider
    hasStoredProvider.value = true
  }
  baseUrl.value = prefs.baseUrl ?? ''
  model.value = prefs.model ?? ''
  advancedOpen.value = !!(baseUrl.value || model.value)
})

function savePrefs() {
  const prefs: ScanPrefs = {
    useLlm: useLlm.value,
    provider: provider.value,
    baseUrl: baseUrl.value.trim() || undefined,
    model: model.value.trim() || undefined
  }
  try {
    localStorage.setItem(PREFS_KEY, JSON.stringify(prefs))
  } catch {
    // Storage can be unavailable (private mode, blocked site data); preferences are optional.
  }
}

// Default to the server's Claude login when it's available, unless the visitor picked before.
watch(() => health.value?.claude_cli_available, (available) => {
  if (available && !hasStoredProvider.value) provider.value = 'claude_cli'
}, { immediate: true })

// Measured on this deployment: static scans of a repo or SKILL.md take about a minute.
const durationHint = computed(() => useLlm.value
  ? 'With AI analysis, a scan usually takes a few minutes.'
  : 'A scan usually takes about a minute.'
)

const depthOptions = computed(() => [
  {
    value: 'static',
    label: 'Static analysis',
    description: '20+ analyzers. Nothing leaves this server.'
  },
  {
    value: 'ai',
    label: 'Static + AI review',
    description: `Adds a semantic read of intent. Slower, and the skill’s content is sent to ${PROVIDER_RECIPIENTS[provider.value]}.`
  }
])

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
    savePrefs()
    await navigateTo(`/scan/${id}`)
  } catch (err) {
    errorMessage.value = apiErrorMessage(err, 'Failed to start scan')
    submitting.value = false
  }
}
</script>

<template>
  <form
    class="flex flex-col gap-5 rounded-2xl border border-default bg-default p-5 shadow-[0_12px_32px_-16px_rgb(21_23_28/0.18)] sm:p-6"
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
      :error="targetProblem"
      :ui="{ label: 'font-semibold text-highlighted' }"
    >
      <div class="flex gap-2 max-sm:flex-col">
        <UInput
          ref="targetInput"
          v-model="target"
          type="url"
          inputmode="url"
          placeholder="https://github.com/org/repo"
          icon="i-lucide-link"
          size="xl"
          class="min-w-0 flex-1"
          :ui="{ base: 'h-14 font-mono text-sm ring-accented focus-visible:ring-2 focus-visible:ring-inverted' }"
          :disabled="submitting"
          @blur="targetTouched = true"
        />
        <UButton
          type="submit"
          color="neutral"
          size="xl"
          trailing-icon="i-lucide-arrow-right"
          class="h-14 justify-center px-6 font-semibold"
          :loading="submitting"
          :disabled="!canSubmit"
        >
          Scan skill
        </UButton>
      </div>
      <template #help>
        <span
          v-if="targetInfo?.ok"
          class="flex min-w-0 items-center gap-1.5"
        >
          <UIcon
            name="i-lucide-check"
            class="size-4 shrink-0 text-primary"
          />
          <span class="shrink-0">{{ targetInfo.host }} · {{ TARGET_KIND_LABELS[targetInfo.kind].label }} ·</span>
          <span class="truncate font-mono text-xs text-highlighted">{{ targetInfo.title }}</span>
        </span>
        <span v-else-if="!target.trim()">
          A repository or a single SKILL.md file on GitHub, GitLab, Bitbucket or Hugging Face.
        </span>
      </template>
    </UFormField>

    <UAlert
      v-if="previousScan"
      color="neutral"
      variant="subtle"
      icon="i-lucide-history"
      :description="previousScan.status === 'done' ? 'Open that result, or scan again for a fresh one.' : 'Follow its progress instead of starting another scan.'"
      :actions="[{ label: previousScan.status === 'done' ? 'View result' : 'Follow scan', to: `/scan/${previousScan.id}`, color: 'neutral', variant: 'outline', trailingIcon: 'i-lucide-arrow-right' }]"
      orientation="horizontal"
    >
      <template #title>
        <template v-if="previousScan.status === 'done'">
          Already scanned <NuxtTime
            :datetime="previousScan.created_at * 1000"
            relative
          /><template v-if="previousScan.recommendation">
            — {{ RECOMMENDATION_LABEL[previousScan.recommendation] }}
          </template>
        </template>
        <template v-else>
          This skill is being scanned right now
        </template>
      </template>
    </UAlert>

    <URadioGroup
      v-model="depth"
      legend="Scan depth"
      variant="card"
      :items="depthOptions"
      :disabled="submitting"
      :ui="{
        legend: 'mb-2.5 font-semibold text-highlighted',
        fieldset: 'grid gap-3 sm:grid-cols-2',
        item: 'rounded-xl border-accented p-4 has-data-[state=checked]:border-primary has-data-[state=checked]:bg-primary/8',
        label: 'font-semibold text-highlighted',
        description: 'mt-1 leading-snug'
      }"
    />

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
        class="flex flex-col gap-3 rounded-xl bg-muted p-4 ring ring-default"
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
          <template
            v-if="API_KEY_LINKS[provider]"
            #hint
          >
            <ULink
              :to="API_KEY_LINKS[provider]"
              target="_blank"
              class="text-xs"
            >
              Get a key
            </ULink>
          </template>
          <UInput
            v-model="apiKey"
            type="password"
            placeholder="sk-..."
            class="w-full"
            :disabled="submitting"
          />
        </UFormField>

        <UAlert
          v-if="claudeCliUnauthenticated"
          color="warning"
          variant="subtle"
          icon="i-lucide-alert-triangle"
          title="Server not logged in"
          description="This server's Claude CLI hasn't been authenticated yet — an admin needs to complete the login before this provider will work."
        />

        <UCollapsible
          v-model:open="advancedOpen"
          class="flex flex-col gap-3"
        >
          <UButton
            label="Advanced options"
            color="neutral"
            variant="link"
            size="xs"
            trailing-icon="i-lucide-chevron-down"
            class="self-start px-0"
            :ui="{ trailingIcon: 'transition-transform group-data-[state=open]:rotate-180' }"
          />

          <template #content>
            <div class="flex flex-col gap-3">
              <UFormField
                v-if="provider !== 'claude_cli'"
                label="Base URL"
                description="Override for a proxy or an OpenAI-compatible endpoint."
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
                description="Leave empty to use the provider’s recommended model."
              >
                <UInput
                  v-model="model"
                  placeholder="Provider default"
                  class="w-full"
                  :disabled="submitting"
                />
              </UFormField>
            </div>
          </template>
        </UCollapsible>
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

    <div class="flex flex-wrap items-center gap-2 border-t border-muted pt-4 text-sm text-muted">
      <template v-if="!target.trim()">
        <span>Try an example:</span>
        <UButton
          v-for="example in EXAMPLES"
          :key="example.target"
          :icon="example.icon"
          :label="example.label"
          size="sm"
          color="neutral"
          variant="outline"
          class="rounded-full"
          :disabled="submitting"
          @click="useExample(example)"
        />
      </template>
      <span v-else>
        {{ durationHint }} You can leave the result page and come back from the history.
      </span>
    </div>
  </form>
</template>
