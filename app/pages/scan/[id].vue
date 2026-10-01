<script setup lang="ts">
import type { Finding, ScanReport, Severity } from '~~/shared/types/scan'

const route = useRoute()
const id = route.params.id as string

const { status, error } = useScanStatus(id)

const isWorking = computed(() => status.value?.status === 'pending' || status.value?.status === 'running')

const { lines: logLines } = useScanLogs(id, isWorking)
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
  `scan-${id}-skill`,
  () => selectedSkill.value?.risk_assessment ? $fetch<ScanReport>(`/api/scan/${id}/skills/${skillIndex.value}`) : Promise.resolve(null),
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
const hiddenSeverities = ref(new Set<string>())
const hiddenCategories = ref(new Set<string>())
const hiddenFiles = ref(new Set<string>())
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
}

const activeFilterCount = computed(() =>
  hiddenSeverities.value.size + hiddenCategories.value.size + hiddenFiles.value.size)

const filteredIssues = computed(() => sortedIssues.value.filter(issue =>
  !hiddenSeverities.value.has(issue.severity)
  && !(issue.category && hiddenCategories.value.has(issue.category))
  && !hiddenFiles.value.has(issue.location.file)
))

const filterGroups = computed(() => [
  { legend: 'Severity', hidden: hiddenSeverities, items: severityCounts.value, mono: false },
  { legend: 'Category', hidden: hiddenCategories, items: categoryCounts.value, mono: true },
  { legend: 'File', hidden: hiddenFiles, items: fileCounts.value, mono: true }
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
      <nav
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
        <UButton
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
      </div>
    </div>

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
          v-if="report.metadata?.transitive_targets_scanned !== undefined"
          class="text-sm text-muted"
        >
          Followed {{ report.metadata.transitive_targets_scanned }} external reference{{ report.metadata.transitive_targets_scanned === 1 ? '' : 's' }}
        </p>
      </VerdictPanel>

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

      <SkillsOverview
        v-if="skills && !selectedSkill"
        :skills="skills"
        :unscanned="status.result?.unscanned_skills ?? []"
      />

      <BaselinePanel
        v-if="report.suppressed?.length || report.generated_baseline && !selectedSkill"
        :scan-id="id"
        :report="report"
        :downloadable="!selectedSkill"
        :active-count="skills && !selectedSkill ? skillFindings : report.issues.length"
      />
    </template>
  </UContainer>
</template>
