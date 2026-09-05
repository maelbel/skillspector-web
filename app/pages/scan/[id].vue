<script setup lang="ts">
import type { Severity } from '~~/shared/types/scan'

const route = useRoute()
const router = useRouter()
const id = route.params.id as string

function goBack() {
  if (window.history.state?.back) {
    router.back()
  } else {
    router.push('/')
  }
}

const { status, error } = useScanStatus(id)

const isWorking = computed(() => status.value?.status === 'pending' || status.value?.status === 'running')

const { lines: logLines } = useScanLogs(id, isWorking)
const showLogs = ref(false)

const parsedTarget = computed(() => parseScanTarget(status.value?.target ?? ''))
const displayTitle = computed(() => {
  const skillName = status.value?.result?.skill.name
  if (skillName && skillName !== 'unknown') return skillName
  return parsedTarget.value.title
})

useSeoMeta({
  title: () => status.value ? `${displayTitle.value} — Skillspector Web` : 'Scan result — Skillspector Web'
})

const SEVERITY_RANK: Record<Severity, number> = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 }

const sortedIssues = computed(() => {
  const issues = status.value?.result?.issues ?? []
  return [...issues].sort((a, b) => SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity])
})

const severityCounts = computed(() => {
  const counts: Record<Severity, number> = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 }
  for (const issue of sortedIssues.value) counts[issue.severity]++
  return (Object.entries(counts) as [Severity, number][]).filter(([, count]) => count > 0)
})

const errorMessage = computed(() => {
  const err = error.value
  if (!err) return undefined
  return (err.data as { statusMessage?: string } | undefined)?.statusMessage ?? err.message
})
</script>

<template>
  <UContainer class="py-16">
    <div class="max-w-2xl mx-auto flex flex-col gap-6">
      <UButton
        icon="i-lucide-arrow-left"
        variant="ghost"
        color="neutral"
        class="self-start"
        @click="goBack"
      >
        Scan another
      </UButton>

      <UAlert
        v-if="errorMessage"
        color="error"
        variant="subtle"
        :title="errorMessage"
      />

      <template v-else-if="isWorking || !status">
        <UCard>
          <div class="flex flex-col gap-4 py-2">
            <div class="flex items-center gap-3">
              <UIcon
                name="i-lucide-loader-circle"
                class="size-5 animate-spin text-primary shrink-0"
              />
              <div>
                <p class="font-medium">
                  Scanning{{ status ? ` ${status.target}` : '…' }}
                </p>
                <p class="text-sm text-muted">
                  Static analysis usually finishes in a few seconds; can take up to ~60s.
                </p>
              </div>
            </div>
            <div class="flex flex-col gap-1">
              <UProgress
                :model-value="status?.completed_steps ?? 0"
                :max="status?.total_steps ?? 1"
              />
              <p class="text-xs text-muted">
                Step {{ status?.completed_steps ?? 0 }} of {{ status?.total_steps ?? '…' }}
              </p>
            </div>
            <ScanLogPanel v-if="logLines.length" :lines="logLines" />
          </div>
        </UCard>
      </template>

      <template v-else-if="status.status === 'error'">
        <UAlert
          color="error"
          variant="subtle"
          title="Scan failed"
          :description="status.error ?? 'Unknown error'"
        />
        <div v-if="logLines.length">
          <UButton
            variant="link"
            color="neutral"
            size="sm"
            class="px-0"
            :icon="showLogs ? 'i-lucide-chevron-down' : 'i-lucide-chevron-right'"
            @click="showLogs = !showLogs"
          >
            {{ showLogs ? 'Hide' : 'View' }} scan log
          </UButton>
          <ScanLogPanel v-if="showLogs" :lines="logLines" class="mt-2" />
        </div>
      </template>

      <template v-else-if="status.result">
        <div>
          <h1 class="text-xl font-bold flex items-center gap-2">
            <UIcon
              v-if="parsedTarget.isGithub"
              name="i-simple-icons-github"
              class="size-5 shrink-0"
            />
            {{ displayTitle }}
          </h1>
          <p class="text-sm text-muted font-mono break-all">
            {{ status.result.skill.source }}
          </p>
        </div>

        <div v-if="logLines.length">
          <UButton
            variant="link"
            color="neutral"
            size="sm"
            class="px-0"
            :icon="showLogs ? 'i-lucide-chevron-down' : 'i-lucide-chevron-right'"
            @click="showLogs = !showLogs"
          >
            {{ showLogs ? 'Hide' : 'View' }} scan log
          </UButton>
          <ScanLogPanel v-if="showLogs" :lines="logLines" class="mt-2" />
        </div>

        <RiskScoreGauge
          :score="status.result.risk_assessment.score"
          :severity="status.result.risk_assessment.severity"
          :recommendation="status.result.risk_assessment.recommendation"
        />

        <UAlert
          v-if="!status.result.execution_successful"
          color="warning"
          variant="subtle"
          title="Analysis was incomplete"
          description="One or more analyzers didn't finish — findings below may be partial."
        />

        <div v-if="sortedIssues.length">
          <div class="mb-3 flex flex-wrap items-center gap-2">
            <h2 class="text-sm font-semibold text-muted uppercase tracking-wide">
              {{ sortedIssues.length }} finding{{ sortedIssues.length === 1 ? '' : 's' }}
            </h2>
            <div class="flex gap-1.5">
              <SeverityBadge
                v-for="[severity, count] in severityCounts"
                :key="severity"
                :severity="severity"
              >
                {{ count }} {{ severity }}
              </SeverityBadge>
            </div>
          </div>
          <div class="flex flex-col gap-3">
            <FindingCard
              v-for="issue in sortedIssues"
              :key="issue.finding_id"
              :finding="issue"
            />
          </div>
        </div>
        <UAlert
          v-else
          color="primary"
          variant="subtle"
          icon="i-lucide-check"
          title="No issues found"
        />
      </template>
    </div>
  </UContainer>
</template>
