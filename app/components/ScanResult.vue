<script setup lang="ts">
import type { Finding, ScanReport, Severity } from '~~/shared/types/scan'

// A scan's result: from /api/scan/<id> for someone with access to it (scanId set), or read-only
// from /api/shared/<token> for anyone with its link (pages/shared/[token].vue).
const props = defineProps<{ apiBase: string, scanId?: string }>()
const shared = computed(() => !props.scanId)

const route = useRoute()

const { status, error } = useScanStatus(props.apiBase)

const isWorking = computed(() => status.value?.status === 'pending' || status.value?.status === 'running')

const { lines: logLines } = useScanLogs(props.scanId ?? null, isWorking)
const showLogs = ref(false)

// A repository holding several skills has one report per skill: ?skill=<index> shows one, loaded
// on demand; without it, the page shows them all.
const skills = computed(() => status.value?.result?.skills ?? null)
const skillIndex = computed(() => {
  const value = route.query.skill
  return typeof value === 'string' && /^\d+$/.test(value) ? Number(value) : null
})
const selectedSkill = computed(() => skillIndex.value === null ? null : skills.value?.[skillIndex.value] ?? null)
const { data: skillReport, error: skillError } = useAsyncData(
  `${props.apiBase}-skill`,
  () => selectedSkill.value?.risk_assessment ? $fetch<ScanReport>(`${props.apiBase}/skills/${skillIndex.value}`) : Promise.resolve(null),
  { watch: [selectedSkill] }
)
// The report on show: one skill's, or the scan's.
const report = computed(() => selectedSkill.value ? skillReport.value : status.value?.result ?? null)
const skillFindings = computed(() => (skills.value ?? []).reduce((sum, skill) => sum + (skill.issue_count ?? 0), 0))
// The overview's verdict is its riskiest skill's.
const overviewSummary = computed(() => {
  if (!skills.value || selectedSkill.value) return undefined
  const scanned = skills.value.filter(skill => skill.risk_assessment)
  const riskiest = [...scanned].sort((a, b) => b.risk_assessment!.score - a.risk_assessment!.score)[0]
  return riskiest ? `The riskiest of ${skills.value.length} skills is ${riskiest.name}. Open a skill for its findings.` : undefined
})
const aiReview = computed(() => selectedSkill.value ? selectedSkill.value.ai_review ?? null : status.value?.ai_review ?? null)

const parsedTarget = computed(() => parseScanTarget(status.value?.target ?? ''))
const displayTitle = computed(() => {
  if (selectedSkill.value) return selectedSkill.value.name
  const skillName = status.value?.result?.skill.name
  if (skillName && skillName !== 'unknown') return skillName
  return parsedTarget.value.title
})
const duration = computed(() => status.value ? scanDurationSeconds(status.value) : null)
const aiModels = computed(() => report.value ? aiReviewModels(report.value) : [])

// Shown when an AI review was asked for but its results are missing in part or in full.
const aiReviewAlert = computed(() => {
  const result = report.value
  const state = aiReview.value
  if (!result || (state !== 'failed' && state !== 'degraded')) return null
  const details = [result.metadata?.llm_error, aiReviewCallSummary(result)].filter(Boolean).join(' ')
  return state === 'failed'
    ? {
        title: 'The AI review didn\'t run',
        description: `The verdict and findings below come from static analysis only. ${details}`.trim()
      }
    : {
        title: 'The AI review only partly ran',
        description: `Some files were only checked by static analysis. ${details}`.trim()
      }
})

const gaps = computed(() => report.value ? inspectionGaps(report.value) : null)

const scanAgainLink = computed(() => status.value ? `/?target=${encodeURIComponent(status.value.target)}` : '/')

// Downloads of the report, and its read-only link (ShareDialog), which only its owner sees.
const exportItems = computed(() => [
  { label: 'JSON (skillspector’s report)', icon: 'i-lucide-file-json', onSelect: () => window.location.assign(`${props.apiBase}/export?format=json`) },
  { label: 'SARIF (code scanning tools)', icon: 'i-lucide-file-code', onSelect: () => window.location.assign(`${props.apiBase}/export?format=sarif`) }
])
const shareOpen = ref(false)
const shareToken = ref<string | null>(null)
watch(() => status.value?.share_token ?? null, (token) => {
  shareToken.value = token
}, { immediate: true })

// The target again, as this scan ran: the new result is compared with this one.
const rescanning = ref(false)
const rescanError = ref('')
async function rescanTarget() {
  rescanning.value = true
  rescanError.value = ''
  try {
    const { id: next } = await $fetch<{ id: string }>(`${props.apiBase}/rescan`, { method: 'POST' })
    await navigateTo(`/scan/${next}`)
  } catch (err) {
    rescanError.value = apiErrorMessage(err, 'Couldn’t rescan')
    rescanning.value = false
  }
}

useSeoMeta({
  title: () => status.value ? `${displayTitle.value} — Skillspector Web` : 'Scan result — Skillspector Web'
})

type SortKey = 'severity' | 'confidence' | 'file'

const SORT_OPTIONS: { label: string, value: SortKey }[] = [
  { label: 'Severity', value: 'severity' },
  { label: 'Confidence', value: 'confidence' },
  { label: 'File', value: 'file' }
]

const sortKey = ref<SortKey>('severity')

const issues = computed(() => report.value?.issues ?? [])

const sortedIssues = computed(() => {
  const list = [...issues.value]
  switch (sortKey.value) {
    case 'confidence':
      return list.sort((a, b) => b.confidence - a.confidence)
    case 'file':
      return list.sort((a, b) =>
        a.location.file.localeCompare(b.location.file) || a.location.start_line - b.location.start_line)
    default:
      return list.sort((a, b) => SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity] || b.confidence - a.confidence)
  }
})

function countBy(key: (issue: Finding) => string | null) {
  const counts = new Map<string, number>()
  for (const issue of issues.value) {
    const value = key(issue)
    if (value) counts.set(value, (counts.get(value) ?? 0) + 1)
  }
  return counts
}

const severityCounts = computed(() => {
  const counts = countBy(issue => issue.severity)
  return SEVERITIES.filter(severity => counts.has(severity)).map(severity => ({ value: severity, count: counts.get(severity)! }))
})
const categoryCounts = computed(() =>
  [...countBy(issue => issue.category)].sort(([a], [b]) => a.localeCompare(b)).map(([value, count]) => ({ value, count }))
)
const fileCounts = computed(() =>
  [...countBy(issue => issue.location.file)].sort(([a], [b]) => a.localeCompare(b)).map(([value, count]) => ({ value, count }))
)

// Filters hold what's hidden, so a new value (or a fresh scan) is shown by default.
const ruleCounts = computed(() =>
  [...countBy(issue => issue.id)].sort(([a], [b]) => a.localeCompare(b, undefined, { numeric: true })).map(([value, count]) => ({ value, count })))
const hiddenSeverities = ref(new Set<string>())
const hiddenCategories = ref(new Set<string>())
const hiddenFiles = ref(new Set<string>())
const hiddenRules = ref(new Set<string>())
const hiddenChanges = ref(new Set<string>())
const CHANGE_LABELS = { new: 'New', unchanged: 'Unchanged' } as const
const changeLabel = (issue: Finding) => issue.change ? CHANGE_LABELS[issue.change] : null
const changeCounts = computed(() =>
  [...countBy(changeLabel)].sort(([a], [b]) => a.localeCompare(b)).map(([value, count]) => ({ value, count })))
const executableCount = computed(() => report.value?.components?.filter(component => component.executable).length ?? 0)

// From the Files section: only that file's findings, then back up to them.
function showOnlyFile(file: string) {
  hiddenFiles.value = new Set(fileCounts.value.map(({ value }) => value).filter(value => value !== file))
  document.getElementById('findings-heading')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}
const filtersOpen = ref(false)

function toggle(set: Ref<Set<string>>, value: string) {
  const next = new Set(set.value)
  if (next.has(value)) {
    next.delete(value)
  } else {
    next.add(value)
  }
  set.value = next
}

function clearFilters() {
  hiddenSeverities.value = new Set()
  hiddenCategories.value = new Set()
  hiddenFiles.value = new Set()
  hiddenRules.value = new Set()
  hiddenChanges.value = new Set()
}

const activeFilterCount = computed(() =>
  hiddenSeverities.value.size + hiddenCategories.value.size + hiddenFiles.value.size + hiddenRules.value.size + hiddenChanges.value.size)

const filteredIssues = computed(() => sortedIssues.value.filter(issue =>
  !hiddenSeverities.value.has(issue.severity)
  && !(issue.category && hiddenCategories.value.has(issue.category))
  && !hiddenFiles.value.has(issue.location.file)
  && !hiddenRules.value.has(issue.id)
  && !hiddenChanges.value.has(changeLabel(issue) ?? '')
))

const filterGroups = computed(() => [
  { legend: 'Severity', hidden: hiddenSeverities, items: severityCounts.value, mono: false },
  { legend: 'Category', hidden: hiddenCategories, items: categoryCounts.value, mono: true },
  { legend: 'File', hidden: hiddenFiles, items: fileCounts.value, mono: true },
  { legend: 'Rule', hidden: hiddenRules, items: ruleCounts.value, mono: true },
  { legend: 'Since the previous scan', hidden: hiddenChanges, items: changeCounts.value, mono: false }
].filter(group => group.items.length > 1 || group.hidden.value.size > 0))

// Sorted by severity, findings sit under one heading per level; other sorts are one flat list.
const groupedIssues = computed(() => {
  if (sortKey.value !== 'severity') return [{ severity: null, issues: filteredIssues.value }]
  return SEVERITIES
    .map(severity => ({ severity: severity as Severity | null, issues: filteredIssues.value.filter(issue => issue.severity === severity) }))
    .filter(group => group.issues.length)
})

// Every finding starts open; the map only records the ones someone has toggled.
const expandedOverrides = ref(new Map<string, boolean>())

function isExpanded(issue: Finding) {
  return expandedOverrides.value.get(findingKey(issue)) ?? true
}

function toggleExpanded(issue: Finding) {
  expandedOverrides.value = new Map(expandedOverrides.value).set(findingKey(issue), !isExpanded(issue))
}

const allExpanded = computed(() =>
  filteredIssues.value.length > 0 && filteredIssues.value.every(issue => isExpanded(issue)))

function toggleAll() {
  const open = !allExpanded.value
  expandedOverrides.value = new Map(sortedIssues.value.map(issue => [findingKey(issue), open]))
}

const errorMessage = computed(() => {
  const err = error.value
  if (!err) return undefined
  return apiErrorMessage(err, err.message)
})
</script>

<template>
  <UContainer class="flex flex-col gap-7 py-8 sm:py-10">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <p
        v-if="shared"
        class="flex min-w-0 items-center gap-2 text-sm text-muted"
      >
        <UIcon
          name="i-lucide-link"
          class="size-4 shrink-0"
        />
        <span>Shared result: read-only</span>
      </p>
      <nav
        v-else
        aria-label="Breadcrumb"
        class="flex min-w-0 items-center gap-2 text-sm text-muted"
      >
        <ULink
          to="/history"
          class="font-medium text-muted hover:text-highlighted"
        >
          History
        </ULink>
        <UIcon
          name="i-lucide-chevron-right"
          class="size-3.5 shrink-0"
        />
        <span class="truncate text-highlighted">{{ status ? displayTitle : 'Scan' }}</span>
      </nav>

      <div
        v-if="status && !isWorking"
        class="flex flex-wrap gap-2"
      >
        <UDropdownMenu
          v-if="status.status === 'done'"
          :items="exportItems"
          :content="{ align: 'end' }"
        >
          <UButton
            icon="i-lucide-download"
            trailing-icon="i-lucide-chevron-down"
            color="neutral"
            variant="outline"
            size="lg"
          >
            Export
          </UButton>
        </UDropdownMenu>
        <UButton
          v-if="scanId && status.status === 'done'"
          :icon="shareToken ? 'i-lucide-link' : 'i-lucide-share-2'"
          color="neutral"
          variant="outline"
          size="lg"
          @click="shareOpen = true"
        >
          {{ shareToken ? 'Shared' : 'Share' }}
        </UButton>
        <UButton
          v-if="shared"
          to="/"
          color="primary"
          size="lg"
        >
          Scan a skill
        </UButton>
        <template v-else>
          <UButton
            v-if="status.rescan"
            icon="i-lucide-rotate-cw"
            color="neutral"
            variant="outline"
            size="lg"
            :loading="rescanning"
            @click="rescanTarget"
          >
            Rescan
          </UButton>
          <!-- An upload isn't kept once scanned, so there's nothing to scan again from; an AI review
             that needs its key again goes through the form. -->
          <UButton
            v-else-if="!isUploadTarget(status.target)"
            :to="scanAgainLink"
            icon="i-lucide-rotate-cw"
            color="neutral"
            variant="outline"
            size="lg"
          >
            Scan again
          </UButton>
          <UButton
            to="/"
            color="primary"
            size="lg"
          >
            New scan
          </UButton>
        </template>
      </div>
    </div>

    <ShareDialog
      v-if="scanId"
      v-model:open="shareOpen"
      v-model:token="shareToken"
      :scan-id="scanId"
    />

    <UAlert
      v-if="rescanError"
      color="error"
      variant="subtle"
      icon="i-lucide-circle-alert"
      title="Couldn’t rescan"
      :description="rescanError"
    />

    <UAlert
      v-if="errorMessage"
      color="error"
      variant="subtle"
      :title="errorMessage"
    />

    <ScanProgress
      v-else-if="isWorking || !status"
      :status="status"
      :title="status ? displayTitle : 'Loading scan…'"
      :lines="logLines"
    />

    <template v-else-if="status.status === 'error'">
      <section class="flex flex-col gap-4 rounded-xs border border-critical-line bg-critical-tint p-6 sm:p-10">
        <p class="eyebrow text-critical-ink">
          Scan failed
        </p>
        <h1 class="display text-4xl leading-tight break-words text-highlighted sm:text-5xl">
          {{ displayTitle }}
        </h1>
        <p class="font-mono text-sm break-all text-muted">
          {{ status.target }}
        </p>
        <p class="max-w-2xl text-base text-highlighted sm:text-lg">
          {{ status.error ?? 'Unknown error' }}
        </p>
      </section>
      <ScanLogPanel
        v-if="logLines.length"
        :lines="logLines"
        tall
      />
    </template>

    <UAlert
      v-else-if="selectedSkill && skillError"
      color="error"
      variant="subtle"
      :title="apiErrorMessage(skillError, 'Couldn’t load this skill’s report')"
    />

    <template v-else-if="report">
      <NuxtLink
        v-if="selectedSkill"
        :to="{ query: {} }"
        class="inline-flex items-center gap-1.5 self-start text-sm font-medium text-muted hover:text-highlighted"
      >
        <UIcon
          name="i-lucide-arrow-left"
          class="size-4"
        />
        All {{ skills?.length }} skills in {{ parsedTarget.title }}
      </NuxtLink>

      <VerdictPanel
        :report="report"
        :summary="overviewSummary"
        :finding-count="skills && !selectedSkill ? skillFindings : undefined"
      >
        <p class="flex items-center gap-2 font-semibold text-highlighted">
          <UIcon
            v-if="parsedTarget.isGithub"
            name="i-simple-icons-github"
            class="size-4 shrink-0"
          />
          <span class="truncate">{{ displayTitle }}</span>
        </p>
        <p class="font-mono text-sm break-all text-muted">
          {{ status.target }}
        </p>
        <p class="text-sm text-muted">
          Scanned <NuxtTime
            :datetime="status.created_at * 1000"
            relative
            :title="formatDate(status.created_at)"
          /><template v-if="duration !== null">
            · took {{ formatDuration(duration) }}
          </template> · {{ status.ai_review ? 'Static + AI review' : 'Static analysis' }}<template v-if="aiModels.length">
            ({{ aiModels.join(', ') }})
          </template><template v-if="logLines.length">
            · <button
              type="button"
              class="cursor-pointer font-medium text-highlighted underline underline-offset-2"
              :aria-expanded="showLogs"
              @click="showLogs = !showLogs"
            >
              {{ showLogs ? 'Hide' : 'View' }} scan log
            </button>
          </template>
        </p>
        <p
          v-if="selectedSkill"
          class="font-mono text-sm text-muted"
        >
          {{ selectedSkill.path }}
        </p>
        <p
          v-if="status.ai_tokens && !selectedSkill"
          class="text-sm text-muted"
        >
          AI review used {{ formatTokenUsage(status.ai_tokens) }} tokens
        </p>
        <p
          v-if="report.metadata?.has_executable_scripts"
          class="flex items-center gap-1.5 text-sm text-highlighted"
        >
          <UIcon
            name="i-lucide-file-terminal"
            class="size-4 shrink-0"
          />
          Contains executable scripts<template v-if="executableCount">
            ({{ executableCount }})
          </template>
        </p>
        <p
          v-if="report.metadata?.transitive_targets_scanned !== undefined"
          class="text-sm text-muted"
        >
          Followed {{ report.metadata.transitive_targets_scanned }} external reference{{ report.metadata.transitive_targets_scanned === 1 ? '' : 's' }}
        </p>
      </VerdictPanel>

      <ScanComparison
        v-if="status.comparison && !selectedSkill"
        :comparison="status.comparison"
        :target="status.target"
        :score="report.risk_assessment.score"
        :recommendation="report.risk_assessment.recommendation"
      />

      <ScanLogPanel
        v-if="showLogs"
        :lines="logLines"
        tall
      />

      <UAlert
        v-if="aiReviewAlert"
        color="warning"
        variant="subtle"
        icon="i-lucide-bot-off"
        :title="aiReviewAlert.title"
        :description="aiReviewAlert.description"
      />

      <UAlert
        v-if="!report.execution_successful && (!skills || selectedSkill)"
        color="warning"
        variant="subtle"
        icon="i-lucide-alert-triangle"
        title="Analysis was incomplete"
        :description="gaps ? 'Part of the analysis didn\'t finish: see what wasn\'t inspected below.' : 'One or more analyzers didn\'t finish, so the findings below may be partial.'"
      />

      <InspectionGaps
        v-if="gaps"
        :gaps="gaps"
      />

      <McpServerPanel
        v-if="report.mcp_server"
        :server="report.mcp_server"
      />

      <div
        v-if="issues.length"
        class="grid items-start gap-6 lg:gap-10"
        :class="{ 'lg:grid-cols-[17rem_minmax(0,1fr)]': filterGroups.length }"
      >
        <aside
          v-if="filterGroups.length"
          aria-label="Filter findings"
          class="flex flex-col gap-4 lg:sticky lg:top-[calc(var(--ui-header-height)+1.5rem)] lg:gap-7 lg:pt-1"
        >
          <UButton
            color="neutral"
            variant="outline"
            icon="i-lucide-filter"
            class="self-start lg:hidden"
            :trailing-icon="filtersOpen ? 'i-lucide-chevron-up' : 'i-lucide-chevron-down'"
            :aria-expanded="filtersOpen"
            @click="filtersOpen = !filtersOpen"
          >
            Filter{{ activeFilterCount ? ` · ${activeFilterCount} hidden` : '' }}
          </UButton>

          <div
            class="flex-col gap-7 lg:flex"
            :class="filtersOpen ? 'flex' : 'hidden'"
          >
            <fieldset
              v-for="group in filterGroups"
              :key="group.legend"
              class="flex flex-col"
            >
              <legend class="eyebrow mb-2.5 text-muted">
                {{ group.legend }}
              </legend>
              <label
                v-for="item in group.items"
                :key="item.value"
                class="flex min-h-10 cursor-pointer items-center gap-2.5 text-sm"
              >
                <input
                  type="checkbox"
                  class="size-4 shrink-0 accent-(--ui-primary)"
                  :checked="!group.hidden.value.has(item.value)"
                  @change="toggle(group.hidden, item.value)"
                >
                <span
                  v-if="group.legend === 'Severity'"
                  class="size-2.5 shrink-0 rounded-xs"
                  :class="SEVERITY_CLASSES[item.value as Severity].dot"
                />
                <span
                  class="min-w-0 flex-1 truncate"
                  :class="[group.mono ? 'font-mono text-[13px]' : '', group.hidden.value.has(item.value) ? 'text-muted' : 'text-highlighted']"
                  :title="item.value"
                >{{ group.legend === 'Severity' ? SEVERITY_LABEL[item.value as Severity] : item.value }}</span>
                <span class="font-mono text-[13px] text-muted tabular-nums">{{ item.count }}</span>
              </label>
            </fieldset>

            <p class="text-sm text-muted">
              Showing {{ filteredIssues.length }} of {{ issues.length }}.
              <button
                v-if="activeFilterCount"
                type="button"
                class="cursor-pointer font-medium text-highlighted underline underline-offset-2"
                @click="clearFilters"
              >
                Show all
              </button>
            </p>
          </div>
        </aside>

        <section
          aria-labelledby="findings-heading"
          class="flex min-w-0 flex-col gap-4"
        >
          <div class="flex flex-wrap items-center justify-between gap-3">
            <h2
              id="findings-heading"
              class="display text-2xl text-highlighted"
            >
              Findings
            </h2>
            <div class="flex items-center gap-4 text-sm">
              <label class="flex items-center gap-2 text-muted">
                Sort
                <USelect
                  v-model="sortKey"
                  :items="SORT_OPTIONS"
                  value-key="value"
                  class="w-36"
                />
              </label>
              <button
                v-if="filteredIssues.length"
                type="button"
                class="h-10 cursor-pointer text-muted underline underline-offset-3 hover:text-highlighted"
                @click="toggleAll"
              >
                {{ allExpanded ? 'Collapse all' : 'Expand all' }}
              </button>
            </div>
          </div>

          <template
            v-for="group in groupedIssues"
            :key="group.severity ?? 'all'"
          >
            <h3
              v-if="group.severity"
              class="eyebrow flex items-center gap-2.5 pt-2"
              :class="SEVERITY_CLASSES[group.severity].ink"
            >
              <span
                class="size-2 rounded-xs"
                :class="SEVERITY_CLASSES[group.severity].dot"
              />
              {{ SEVERITY_LABEL[group.severity] }} · {{ group.issues.length }}
            </h3>
            <FindingCard
              v-for="issue in group.issues"
              :key="findingKey(issue)"
              :finding="issue"
              :expanded="isExpanded(issue)"
              :target="status?.target"
              :skill-path="selectedSkill?.path"
              @toggle="toggleExpanded(issue)"
            />
          </template>

          <UAlert
            v-if="!filteredIssues.length"
            color="neutral"
            variant="subtle"
            icon="i-lucide-filter-x"
            title="No findings match your filters"
            :actions="[{ label: 'Show all', color: 'neutral', variant: 'outline', onClick: clearFilters }]"
          />
        </section>
      </div>

      <FileInventory
        v-if="report.components?.length || report.structured_summaries?.length"
        :report="report"
        :target="status.target"
        :skill-path="selectedSkill?.path"
        @show-file="showOnlyFile"
      />

      <SkillsOverview
        v-if="skills && !selectedSkill"
        :skills="skills"
        :unscanned="status.result?.unscanned_skills ?? []"
      />

      <BaselinePanel
        v-if="report.suppressed?.length || report.generated_baseline && !selectedSkill"
        :scan-id="scanId ?? ''"
        :report="report"
        :downloadable="!selectedSkill && !shared"
        :active-count="skills && !selectedSkill ? skillFindings : report.issues.length"
      />
    </template>
  </UContainer>
</template>
