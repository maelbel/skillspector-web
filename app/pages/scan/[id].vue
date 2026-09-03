<script setup lang="ts">
import type { Severity } from '~~/shared/types/scan'

const route = useRoute()
const id = route.params.id as string

const { status, error } = useScanStatus(id)

useSeoMeta({ title: 'Scan result — Skillspector Web' })

const SEVERITY_RANK: Record<Severity, number> = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 }

const sortedIssues = computed(() => {
  const issues = status.value?.result?.issues ?? []
  return [...issues].sort((a, b) => SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity])
})

const isWorking = computed(() => status.value?.status === 'pending' || status.value?.status === 'running')

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
        to="/"
        icon="i-lucide-arrow-left"
        variant="ghost"
        color="neutral"
        class="self-start"
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
          <div class="flex items-center gap-3 py-4">
            <UIcon
              name="i-lucide-loader-circle"
              class="size-5 animate-spin text-primary"
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
        </UCard>
      </template>

      <template v-else-if="status.status === 'error'">
        <UAlert
          color="error"
          variant="subtle"
          title="Scan failed"
          :description="status.error ?? 'Unknown error'"
        />
      </template>

      <template v-else-if="status.result">
        <div>
          <h1 class="text-xl font-bold">
            {{ status.result.skill.name }}
          </h1>
          <p class="text-sm text-muted font-mono break-all">
            {{ status.result.skill.source }}
          </p>
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
          <h2 class="mb-3 text-sm font-semibold text-muted uppercase tracking-wide">
            {{ sortedIssues.length }} finding{{ sortedIssues.length === 1 ? '' : 's' }}
          </h2>
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
