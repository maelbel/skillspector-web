<script setup lang="ts">
import type { LLMConfig, LLMProvider } from '~~/shared/types/scan'
import type { ScanTargetKind } from '~~/shared/utils/scan'

// Awaited so the server-rendered default provider matches the client's (see the watch below).
const { data: health, pending: healthPending } = await useHealth()

const PROVIDER_LABELS: Record<LLMProvider, string> = {
  anthropic: 'Anthropic',
  openai: 'OpenAI',
  azure_openai: 'Azure OpenAI',
  openai_compatible: 'OpenAI-compatible API (Groq, Together, Mistral…)',
  nv_build: 'NVIDIA build.nvidia.com',
  ollama: 'Ollama (self-hosted)',
  claude_cli: 'Claude via this server — no key needed'
}

const PROVIDER_RECIPIENTS: Record<LLMProvider, string> = {
  anthropic: 'Anthropic',
  openai: 'OpenAI (or the endpoint you set)',
  azure_openai: 'your Azure OpenAI resource',
  openai_compatible: 'the API at the endpoint you set',
  nv_build: 'NVIDIA',
  ollama: 'your Ollama server',
  claude_cli: 'Anthropic, through this server’s Claude login'
}

const API_KEY_LINKS: Partial<Record<LLMProvider, string>> = {
  anthropic: 'https://console.anthropic.com/settings/keys',
  openai: 'https://platform.openai.com/api-keys',
  azure_openai: 'https://portal.azure.com/#view/Microsoft_Azure_ProjectOxford/CognitiveServicesHub/~/OpenAI',
  nv_build: 'https://build.nvidia.com/settings/api-keys'
}

// Providers that only work with an endpoint of the user's (scanner.NEEDS_BASE_URL on the API).
const NEEDS_ENDPOINT: LLMProvider[] = ['azure_openai', 'openai_compatible']

const PROVIDER_ICONS: Record<LLMProvider, string> = {
  anthropic: 'i-simple-icons-anthropic',
  openai: 'i-simple-icons-openai',
  azure_openai: 'i-simple-icons-microsoftazure',
  openai_compatible: 'i-lucide-plug',
  nv_build: 'i-simple-icons-nvidia',
  ollama: 'i-simple-icons-ollama',
  claude_cli: 'i-lucide-terminal'
}

const { session } = useAuth()
// A hosted server offers Claude only: no shared login, no other providers.
const hosted = computed(() => health.value?.mode === 'hosted')

const providerOptions = computed(() => {
  const claudeCliLabel = healthPending.value
    ? 'Claude CLI (checking availability…)'
    : PROVIDER_LABELS.claude_cli

  type ProviderOption = { value: LLMProvider, label: string, icon: string, disabled?: boolean }
  const claudeCli: ProviderOption = { value: 'claude_cli', label: claudeCliLabel, icon: PROVIDER_ICONS.claude_cli, disabled: healthPending.value }
  const withKey: ProviderOption[] = [
    { value: 'anthropic', label: PROVIDER_LABELS.anthropic, icon: PROVIDER_ICONS.anthropic },
    { value: 'openai', label: PROVIDER_LABELS.openai, icon: PROVIDER_ICONS.openai },
    { value: 'azure_openai', label: PROVIDER_LABELS.azure_openai, icon: PROVIDER_ICONS.azure_openai },
    { value: 'nv_build', label: PROVIDER_LABELS.nv_build, icon: PROVIDER_ICONS.nv_build },
    { value: 'openai_compatible', label: PROVIDER_LABELS.openai_compatible, icon: PROVIDER_ICONS.openai_compatible },
    { value: 'ollama', label: PROVIDER_LABELS.ollama, icon: PROVIDER_ICONS.ollama }
  ]
  if (hosted.value) return withKey.filter(option => option.value === 'anthropic')
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
// An MCP server is checked from its registry entry alone: the depth and the options, which are
// about a skill's code, don't apply to it.
const isMcpServer = computed(() => !file.value && targetInfo.value?.ok === true && targetInfo.value.kind === 'mcp')

// A skill uploaded from this computer instead of a link: a .zip, or a SKILL.md on its own. Offered
// when the server takes uploads, which it holds only until the scan ends (backend/app/uploads.py).
const uploadStore = computed(() => health.value?.upload_store ?? null)
const file = ref<File | null>(null)
const fileError = ref('')
const fileInput = ref<HTMLInputElement>()
const dragging = ref(false)

function pickFile(picked: File | null | undefined) {
  fileError.value = ''
  if (!picked) return
  const maxBytes = health.value?.max_upload_bytes ?? 0
  if (!/\.(zip|md)$/i.test(picked.name)) {
    fileError.value = 'Upload a .zip of the skill, or its SKILL.md'
  } else if (picked.size > maxBytes) {
    fileError.value = `${picked.name} is larger than ${formatBytes(maxBytes)}`
  } else {
    file.value = picked
  }
}

function onFileInput(event: Event) {
  const input = event.target as HTMLInputElement
  pickFile(input.files?.[0])
  // Picking the same file again still fires a change.
  input.value = ''
}

function onDrop(event: DragEvent) {
  dragging.value = false
  if (uploadStore.value && !submitting.value) pickFile(event.dataTransfer?.files?.[0])
}

function clearFile() {
  file.value = null
  fileError.value = ''
  nextTick(() => targetInput.value?.inputRef?.focus())
}

// Point at an existing result before starting a duplicate scan of the same URL.
const { data: recentScans } = useRecentScans()
// As the API stores it: an MCP server's name becomes its registry entry's URL.
const normalizeTarget = (value: string) => {
  const server = parseMcpServer(value)
  return server ? mcpEntryUrl(server) : value.trim().replace(/\/+$/, '')
}
const previousScan = computed(() => {
  if (file.value || !targetInfo.value?.ok) return undefined
  const wanted = normalizeTarget(target.value)
  return recentScans.value?.items.find(scan => scan.status !== 'error' && normalizeTarget(scan.target) === wanted)
})

// Real, stable targets: a published skill, a skillspector test fixture that's flagged
// DO_NOT_INSTALL even without AI analysis, and a well-known MCP server.
const EXAMPLES = [
  { label: 'Anthropic’s PDF skill', icon: 'i-lucide-file-text', target: 'https://github.com/anthropics/skills/blob/main/skills/pdf/SKILL.md' },
  { label: 'A poisoned MCP tool', icon: 'i-lucide-skull', target: 'https://github.com/NVIDIA/skillspector/blob/main/tests/fixtures/mcp_poisoned_tool/SKILL.md' },
  { label: 'GitHub’s MCP server', icon: 'i-lucide-server', target: 'io.github.github/github-mcp-server' }
]

function useExample(example: typeof EXAMPLES[number]) {
  target.value = example.target
  targetTouched.value = true
  // The clicked chip disappears once the field is filled; keep focus in the form so Enter scans.
  targetInput.value?.inputRef?.focus()
}

const TARGET_KIND_LABELS: Record<ScanTargetKind, { icon: string, label: string }> = {
  repository: { icon: 'i-lucide-git-branch', label: 'repository' },
  folder: { icon: 'i-lucide-folder', label: 'folder' },
  file: { icon: 'i-lucide-file-text', label: 'single file' },
  archive: { icon: 'i-lucide-file-archive', label: 'archive' },
  mcp: { icon: 'i-lucide-server', label: 'MCP server' }
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
// Default provider, unless the visitor picked one before: their own saved Claude key first, then
// the server's Claude login when it's available.
watch([() => session.value?.claude_key, () => health.value?.claude_cli_available], ([saved, cliAvailable]) => {
  if (hasStoredProvider.value) return
  if (saved) provider.value = 'anthropic'
  else if (cliAvailable) provider.value = 'claude_cli'
}, { immediate: true })

// A remembered provider this server doesn't offer (e.g. after it became hosted) falls back to Claude.
watch([hosted, provider], ([isHosted, current]) => {
  if (isHosted && current !== 'anthropic') provider.value = 'anthropic'
}, { immediate: true })

// Measured on this deployment: static scans of a repo or SKILL.md take about a minute.
const durationHint = computed(() => {
  if (isMcpServer.value) return 'Checking an MCP server takes a few seconds.'
  return useLlm.value
    ? 'With AI analysis, a scan usually takes a few minutes.'
    : 'A scan usually takes about a minute.'
})

const depthOptions = [
  { value: 'static', label: 'Static analysis' },
  { value: 'ai', label: 'Static + AI review' }
]
const DEPTH_HELP = 'Static analysis: 20+ analyzers, and nothing leaves this server. '
  + 'Static + AI review: adds a semantic read of the skill’s intent. Slower, and its content is sent to the AI provider.'

// The Claude key saved to the user's account (app/claude_key.py on the API), used unless they
// choose to paste a different one for this scan.
const savedKey = computed(() => session.value?.claude_key ?? null)
const useOtherKey = ref(false)
const usingSavedKey = computed(() => provider.value === 'anthropic' && !!savedKey.value && !useOtherKey.value)
const needsApiKey = computed(() => provider.value !== 'ollama' && provider.value !== 'claude_cli' && !usingSavedKey.value)
const claudeCliUnauthenticated = computed(() =>
  provider.value === 'claude_cli' && !healthPending.value && !health.value?.claude_cli_available
)
const backendDown = computed(() => health.value?.status === 'down')
const canSubmit = computed(() => {
  if (backendDown.value) return false
  if (!file.value && !targetInfo.value?.ok) return false
  if (isMcpServer.value) return true
  if (useLlm.value && needsApiKey.value && !apiKey.value.trim()) return false
  if (useLlm.value && needsEndpoint.value && !baseUrl.value.trim()) return false
  if (useLlm.value && claudeCliUnauthenticated.value) return false
  return true
})

const needsEndpoint = computed(() => NEEDS_ENDPOINT.includes(provider.value))
const baseUrlPlaceholder = computed(() => {
  switch (provider.value) {
    case 'ollama':
      return 'http://host.docker.internal:11434/v1'
    case 'openai':
      return 'https://api.openai.com/v1 (or an OpenAI-compatible endpoint)'
    case 'azure_openai':
      return 'https://your-resource.openai.azure.com'
    case 'openai_compatible':
      return 'https://api.groq.com/openai/v1'
    default:
      return 'https://api.anthropic.com'
  }
})

// skillspector's known models for the provider (GET /api/models), offered first; any other model
// can still be typed in.
const { data: modelCatalog } = useFetch<Record<string, { default: string | null, models: string[] }>>('/api/models', { key: 'models', lazy: true })
const modelItems = computed(() => {
  const known = modelCatalog.value?.[provider.value]?.models ?? []
  return model.value && !known.includes(model.value) ? [model.value, ...known] : known
})
const modelDefault = computed(() => modelCatalog.value?.[provider.value]?.default)

// An optional skillspector baseline: findings it accepts don't count. Read in the browser and sent
// as text; the API checks it before queueing the scan.
const MAX_BASELINE_BYTES = 256 * 1024
// skillspector's example of the format, at the version the API pins (backend/pyproject.toml).
const BASELINE_FORMAT_DOCS = 'https://github.com/NVIDIA/SkillSpector/blob/v2.12.0/docs/SUPPRESSION.md#baseline-file-format'
const baselineInput = ref<HTMLInputElement>()
const baseline = ref<{ name: string, text: string } | null>(null)
const baselineError = ref('')

async function pickBaseline(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  baselineError.value = ''
  if (!file) return
  if (file.size > MAX_BASELINE_BYTES) {
    baselineError.value = `${file.name} is larger than ${MAX_BASELINE_BYTES / 1024} KB`
    baseline.value = null
  } else {
    baseline.value = { name: file.name, text: await file.text() }
  }
  // Picking the same file again still fires a change.
  if (baselineInput.value) baselineInput.value.value = ''
}

// Following the skill's external references (Git repositories and raw files it links to), as deep
// as the server allows.
const followReferences = ref(false)
const referenceDepth = ref(1)
const maxReferenceDepth = computed(() => health.value?.transitive_max_depth ?? 0)
const referenceDepthOptions = computed(() => Array.from({ length: maxReferenceDepth.value }, (_, i) => ({
  label: i === 0 ? '1 level: what the skill links to' : `${i + 1} levels: and what those link to`,
  value: i + 1
})))

// Baseline and references are rarely needed, so they sit behind "More options"; its label says
// what's set, so nothing hidden is applied unnoticed.
const moreOpen = ref(false)
const moreSummary = computed(() => {
  const set = []
  if (baseline.value) set.push(`baseline: ${baseline.value.name}`)
  if (followReferences.value && maxReferenceDepth.value) {
    set.push(`references: ${referenceDepth.value} level${referenceDepth.value === 1 ? '' : 's'}`)
  }
  return set.join(' · ')
})

// Self-hosted, the file goes with the scan; hosted, to the Blob store first, as function request
// bodies are limited to 4.5 MB (server/api/scan/upload-token.post.ts).
async function submitUpload(picked: File, options: Record<string, unknown>): Promise<{ id: string }> {
  if (uploadStore.value === 'blob') {
    const { upload } = await import('@vercel/blob/client')
    const blob = await upload(`uploads/${session.value?.user?.id ?? 'anonymous'}/${picked.name}`, picked, {
      access: 'private',
      handleUploadUrl: '/api/scan/upload-token'
    })
    return await $fetch<{ id: string }>('/api/scan', { method: 'POST', body: { upload: { pathname: blob.pathname, name: picked.name }, ...options } })
  }
  const form = new FormData()
  form.append('file', picked)
  form.append('options', JSON.stringify(options))
  return await $fetch<{ id: string }>('/api/scan/upload', { method: 'POST', body: form })
}

async function submit() {
  targetTouched.value = true
  if (!canSubmit.value) return

  submitting.value = true
  errorMessage.value = ''

  const forCode = !isMcpServer.value
  const llm: LLMConfig | undefined = forCode && useLlm.value
    ? {
        provider: provider.value,
        useSavedKey: usingSavedKey.value || undefined,
        apiKey: usingSavedKey.value ? undefined : apiKey.value.trim() || undefined,
        baseUrl: baseUrl.value.trim() || undefined,
        model: model.value.trim() || undefined
      }
    : undefined

  const options = {
    llm,
    baseline: forCode ? baseline.value?.text : undefined,
    transitiveDepth: forCode && followReferences.value && maxReferenceDepth.value ? referenceDepth.value : undefined
  }

  try {
    const { id } = file.value
      ? await submitUpload(file.value, options)
      : await $fetch<{ id: string }>('/api/scan', { method: 'POST', body: { target: target.value.trim(), ...options } })
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
    class="surface relative flex flex-col gap-5 rounded-xs p-4 sm:p-5"
    @submit.prevent="submit"
    @dragover.prevent="dragging = !!uploadStore"
    @dragleave.self="dragging = false"
    @drop.prevent="onDrop"
  >
    <div
      v-if="dragging"
      class="pointer-events-none absolute inset-0 z-10 flex items-center justify-center gap-2 rounded-xs bg-default/90 font-semibold text-highlighted ring-2 ring-brand ring-inset"
    >
      <UIcon
        name="i-lucide-upload"
        class="size-5"
      />
      Drop a .zip or SKILL.md to scan it
    </div>

    <UAlert
      v-if="backendDown"
      color="warning"
      variant="subtle"
      icon="i-lucide-server-off"
      title="The scanner is unavailable right now"
      description="The scan service isn’t responding, so new scans can’t start. Past results in the history are still available."
    />

    <UFormField
      label="Skill or MCP server"
      :error="fileError || (file ? undefined : targetProblem)"
      :ui="{ label: 'font-semibold text-highlighted' }"
    >
      <div class="flex gap-2 rounded-xs bg-muted p-1.5 ring-1 ring-default transition-shadow focus-within:ring-2 focus-within:ring-brand max-sm:flex-col">
        <div
          v-if="file"
          class="flex h-12 min-w-0 flex-1 items-center gap-2 px-3"
        >
          <UIcon
            :name="file.name.toLowerCase().endsWith('.zip') ? 'i-lucide-file-archive' : 'i-lucide-file-text'"
            class="size-5 shrink-0 text-dimmed"
          />
          <span class="truncate font-mono text-sm text-highlighted">{{ file.name }}</span>
          <span class="shrink-0 text-xs text-muted">{{ formatBytes(file.size) }}</span>
          <UButton
            icon="i-lucide-x"
            color="neutral"
            variant="ghost"
            size="sm"
            class="ml-auto"
            aria-label="Remove the file, to scan a link instead"
            :disabled="submitting"
            @click="clearFile"
          />
        </div>
        <UInput
          v-else
          id="scan-target"
          ref="targetInput"
          v-model="target"
          type="text"
          inputmode="url"
          autocapitalize="off"
          autocomplete="off"
          spellcheck="false"
          placeholder="https://github.com/org/repo"
          icon="i-lucide-link"
          size="xl"
          class="min-w-0 flex-1"
          variant="none"
          :ui="{ base: 'h-12 font-mono text-sm', leadingIcon: 'text-dimmed' }"
          :disabled="submitting"
          @blur="targetTouched = true"
        />
        <UButton
          type="submit"
          color="primary"
          size="xl"
          trailing-icon="i-lucide-arrow-right"
          class="h-12 justify-center px-6 font-semibold shadow-sm"
          :loading="submitting"
          :disabled="!canSubmit"
        >
          {{ isMcpServer ? 'Scan server' : 'Scan skill' }}
        </UButton>
      </div>
      <template #help>
        <span v-if="file">
          Uploaded for this scan only, and deleted once it’s scanned.
        </span>
        <span
          v-else-if="targetInfo?.ok"
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
          A repository, a folder in one, or a single SKILL.md file on GitHub, GitLab, Bitbucket or Hugging Face, or an MCP server’s name in the MCP Registry.
          <template v-if="uploadStore">
            Or <button
              type="button"
              class="cursor-pointer font-medium text-highlighted underline underline-offset-2 hover:text-brand"
              :disabled="submitting"
              @click="fileInput?.click()"
            >upload a .zip or SKILL.md</button>, or drop one here.
          </template>
        </span>
        <input
          ref="fileInput"
          type="file"
          accept=".zip,.md,application/zip,text/markdown"
          class="hidden"
          @change="onFileInput"
        >
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
          This {{ isMcpServer ? 'server' : 'skill' }} is being scanned right now
        </template>
      </template>
    </UAlert>

    <p
      v-if="isMcpServer"
      class="flex gap-2 rounded-xs bg-muted p-3 text-sm text-muted ring ring-default"
    >
      <UIcon
        name="i-lucide-server"
        class="mt-0.5 size-4 shrink-0"
      />
      <span>
        Checks the server’s entry in the MCP Registry: that its packages are pinned to exact versions
        with valid hashes, that it names its source repository, that it’s still active, and that its
        remote endpoints use HTTPS. Nothing is installed or run.
      </span>
    </p>

    <URadioGroup
      v-if="!isMcpServer"
      v-model="depth"
      variant="card"
      orientation="horizontal"
      :items="depthOptions"
      :disabled="submitting"
      :ui="{
        legend: 'mb-2 flex items-center gap-1.5 font-semibold text-highlighted',
        fieldset: 'flex flex-wrap gap-2',
        item: 'rounded-xs border-default px-3 py-2 has-data-[state=checked]:border-brand has-data-[state=checked]:bg-nv-50 dark:has-data-[state=checked]:bg-nv-950/70',
        label: 'font-medium text-highlighted'
      }"
    >
      <template #legend>
        Scan depth
        <UTooltip
          :text="DEPTH_HELP"
          :content="{ side: 'top' }"
          :ui="{ content: 'max-w-xs h-auto whitespace-normal py-1.5' }"
        >
          <UIcon
            name="i-lucide-info"
            class="size-4 text-muted"
            tabindex="0"
            :aria-label="DEPTH_HELP"
          />
        </UTooltip>
      </template>
    </URadioGroup>

    <Transition
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="opacity-0 -translate-y-1"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition duration-150 ease-in"
      leave-from-class="opacity-100 translate-y-0"
      leave-to-class="opacity-0 -translate-y-1"
    >
      <div
        v-if="useLlm && !isMcpServer"
        class="flex flex-col gap-3 rounded-xs bg-muted p-4 ring ring-default"
      >
        <p class="text-sm text-muted">
          Adds a semantic read of the skill’s intent. Slower, and the skill’s content is sent to {{ PROVIDER_RECIPIENTS[provider] }}.
        </p>
        <UFormField label="Provider">
          <USelect
            id="scan-provider"
            v-model="provider"
            :items="providerOptions"
            value-key="value"
            class="w-full"
            :disabled="submitting"
            :loading="healthPending"
          />
        </UFormField>

        <div
          v-if="usingSavedKey"
          class="flex flex-wrap items-center justify-between gap-2 border-l-[3px] border-brand bg-default px-3 py-2.5 text-sm"
        >
          <span class="flex items-center gap-2 text-default">
            <UIcon
              name="i-lucide-plug"
              class="size-4 shrink-0 text-brand-ink"
            />
            Using your saved Claude key
            <code class="font-mono text-xs text-highlighted">{{ savedKey?.hint }}</code>
          </span>
          <button
            type="button"
            class="cursor-pointer text-xs font-semibold text-muted underline underline-offset-2 hover:text-highlighted"
            @click="useOtherKey = true"
          >
            Use a different key for this scan
          </button>
        </div>

        <UFormField
          v-if="needsApiKey"
          label="API key"
          :description="hosted
            ? 'Used only for this scan: held encrypted until it has run, then deleted.'
            : 'Sent only for this scan, used to call the provider directly, never stored.'"
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
          <PasswordInput
            id="scan-api-key"
            v-model="apiKey"
            subject="API key"
            placeholder="sk-..."
            class="w-full"
            :disabled="submitting"
          />
          <template
            v-if="provider === 'anthropic' && savedKey"
            #help
          >
            <button
              type="button"
              class="cursor-pointer font-semibold underline underline-offset-2 hover:text-highlighted"
              @click="useOtherKey = false; apiKey = ''"
            >
              Use my saved key ({{ savedKey.hint }}) instead
            </button>
          </template>
          <template
            v-else-if="provider === 'anthropic' && session?.claude_key_available"
            #help
          >
            Tired of pasting it? <ULink
              to="/account"
              class="font-semibold underline underline-offset-2"
            >Save your key to your account</ULink>.
          </template>
        </UFormField>

        <UFormField
          v-if="needsEndpoint"
          :label="provider === 'azure_openai' ? 'Endpoint' : 'Base URL'"
          :description="provider === 'azure_openai' ? 'Your Azure OpenAI resource’s endpoint.' : 'The API’s OpenAI-compatible base URL.'"
          required
        >
          <UInput
            id="scan-endpoint"
            v-model="baseUrl"
            :placeholder="baseUrlPlaceholder"
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
                v-if="provider !== 'claude_cli' && provider !== 'nv_build' && !needsEndpoint && !hosted"
                label="Base URL"
                description="Override for a proxy or an OpenAI-compatible endpoint."
              >
                <UInput
                  id="scan-base-url"
                  v-model="baseUrl"
                  :placeholder="baseUrlPlaceholder"
                  class="w-full"
                  :disabled="submitting"
                />
              </UFormField>

              <UFormField
                :label="provider === 'azure_openai' ? 'Deployment' : 'Model'"
                :description="provider === 'azure_openai'
                  ? 'The name of your Azure deployment. Leave empty to use one named after skillspector’s default model.'
                  : 'Pick one skillspector knows, or type any other. Leave empty for the provider’s recommended model.'"
              >
                <USelectMenu
                  id="scan-model"
                  v-model="model"
                  :items="modelItems"
                  create-item
                  :placeholder="modelDefault ? `Default: ${modelDefault}` : 'Provider default'"
                  class="w-full"
                  :disabled="submitting"
                  @create="(item: string) => { model = item }"
                />
              </UFormField>
            </div>
          </template>
        </UCollapsible>
      </div>
    </Transition>

    <UCollapsible
      v-if="!isMcpServer"
      v-model:open="moreOpen"
      class="flex flex-col gap-4"
    >
      <UButton
        color="neutral"
        variant="link"
        size="sm"
        trailing-icon="i-lucide-chevron-down"
        class="self-start px-0 text-left"
        :ui="{ trailingIcon: 'transition-transform group-data-[state=open]:rotate-180' }"
      >
        <span>
          More options<span
            v-if="moreSummary"
            class="font-normal text-muted"
          > · {{ moreSummary }}</span>
        </span>
      </UButton>

      <template #content>
        <div class="flex flex-col gap-5 border-l-2 border-muted pl-4">
          <div class="flex flex-col gap-1.5">
            <p class="flex items-center gap-1.5 font-semibold text-highlighted">
              Baseline
              <UTooltip text="What a baseline file looks like">
                <ULink
                  :to="BASELINE_FORMAT_DOCS"
                  target="_blank"
                  aria-label="What a baseline file looks like, in skillspector's documentation"
                  class="inline-flex text-muted hover:text-highlighted"
                >
                  <UIcon
                    name="i-lucide-info"
                    class="size-4"
                  />
                </ULink>
              </UTooltip>
            </p>
            <p class="text-sm text-muted">
              A <code class="font-mono text-xs">.skillspector-baseline.yaml</code> file: findings it accepts are
              suppressed and don’t count towards the score. Download one from a scan’s result page.
            </p>
            <div class="mt-1 flex flex-wrap items-center gap-2">
              <input
                ref="baselineInput"
                type="file"
                accept=".yaml,.yml,.json,application/json,application/yaml,text/yaml"
                class="sr-only"
                aria-label="Baseline file"
                :disabled="submitting"
                @change="pickBaseline"
              >
              <UButton
                :label="baseline ? 'Replace file' : 'Choose a file'"
                icon="i-lucide-file-check"
                size="sm"
                color="neutral"
                variant="outline"
                class="rounded-xs"
                :disabled="submitting"
                @click="baselineInput?.click()"
              />
              <template v-if="baseline">
                <span class="font-mono text-xs text-highlighted">{{ baseline.name }}</span>
                <UButton
                  icon="i-lucide-x"
                  size="xs"
                  color="neutral"
                  variant="ghost"
                  aria-label="Remove the baseline"
                  :disabled="submitting"
                  @click="baseline = null"
                />
              </template>
            </div>
            <p
              v-if="baselineError"
              class="text-sm text-critical-ink"
            >
              {{ baselineError }}
            </p>
          </div>

          <div
            v-if="maxReferenceDepth"
            class="flex flex-col gap-2"
          >
            <USwitch
              v-model="followReferences"
              label="Follow external references"
              description="Also scan the Git repositories and raw files the skill links to, and mark what's found there. Slower."
              :disabled="submitting"
            />
            <USelect
              v-if="followReferences && maxReferenceDepth > 1"
              v-model="referenceDepth"
              :items="referenceDepthOptions"
              aria-label="How deep to follow references"
              class="w-full sm:max-w-xs"
              :disabled="submitting"
            />
          </div>
        </div>
      </template>
    </UCollapsible>

    <UAlert
      v-if="errorMessage"
      color="error"
      variant="subtle"
      icon="i-lucide-circle-alert"
      title="Couldn’t start the scan"
      :description="errorMessage"
    />

    <div class="flex flex-wrap items-center gap-2 px-1 pb-1 text-sm text-muted">
      <template v-if="!target.trim() && !file">
        <span>Try an example:</span>
        <UButton
          v-for="example in EXAMPLES"
          :key="example.target"
          :icon="example.icon"
          :label="example.label"
          size="sm"
          color="neutral"
          variant="outline"
          class="rounded-xs"
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
