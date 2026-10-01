<script setup lang="ts">
import type { BaselineDownload, ScanReport } from '~~/shared/types/scan'

const props = withDefaults(defineProps<{
  scanId: string
  report: ScanReport
  // One skill of several shows its suppressed findings; the baseline downloads for the whole scan.
  downloadable?: boolean
  activeCount?: number
}>(), { downloadable: true, activeCount: undefined })

const active = computed(() => props.activeCount ?? props.report.issues.length)

const suppressed = computed(() => props.report.suppressed ?? [])
const showSuppressed = ref(false)

const reason = ref('')
const downloading = ref(false)
const downloadError = ref('')

// The baseline lists every active finding as accepted, with the reason given (or skillspector's
// default). Scanning again with it suppresses exactly those findings.
async function download() {
  downloading.value = true
  downloadError.value = ''
  try {
    const { filename, content } = await $fetch<BaselineDownload>(`/api/scan/${props.scanId}/baseline`, {
      query: reason.value.trim() ? { reason: reason.value.trim() } : undefined
    })
    const url = URL.createObjectURL(new Blob([content], { type: 'application/yaml' }))
    const link = Object.assign(document.createElement('a'), { href: url, download: filename })
    link.click()
    URL.revokeObjectURL(url)
  } catch (err) {
    downloadError.value = apiErrorMessage(err, 'Couldn’t download the baseline')
  } finally {
    downloading.value = false
  }
}
</script>

<template>
  <section
    aria-labelledby="baseline-title"
    class="surface flex flex-col gap-4 px-4 py-4 sm:px-5"
  >
    <h2
      id="baseline-title"
      class="font-semibold text-highlighted"
    >
      Baseline
    </h2>

    <div
      v-if="suppressed.length"
      class="flex flex-col gap-2"
    >
      <button
        type="button"
        class="flex cursor-pointer items-center gap-2 self-start text-sm text-default"
        :aria-expanded="showSuppressed"
        @click="showSuppressed = !showSuppressed"
      >
        <UIcon
          :name="showSuppressed ? 'i-lucide-chevron-down' : 'i-lucide-chevron-right'"
          class="size-4 text-muted"
        />
        {{ suppressed.length }} finding{{ suppressed.length === 1 ? '' : 's' }} suppressed by the baseline, not counted in the score
      </button>
      <ul
        v-if="showSuppressed"
        class="flex flex-col"
      >
        <li
          v-for="finding in suppressed"
          :key="findingKey(finding)"
          class="flex flex-col gap-0.5 border-t border-muted py-2.5 text-sm"
        >
          <p class="flex flex-wrap items-baseline gap-x-2">
            <span class="font-medium text-highlighted">{{ findingTitle(finding) }}</span>
            <span class="font-mono text-xs text-muted">{{ finding.id }} · {{ findingLocation(finding) }}</span>
          </p>
          <p class="text-muted">
            {{ finding.suppression_reason }}
          </p>
        </li>
      </ul>
    </div>

    <form
      v-if="report.generated_baseline && downloadable"
      class="flex flex-col gap-2"
      @submit.prevent="download"
    >
      <p class="text-sm text-muted">
        Accept this scan’s {{ active }} active finding{{ active === 1 ? '' : 's' }}:
        scan again with the file as its baseline, and only new findings count.
        Changes to the files or a new skillspector version bring them back.
      </p>
      <div class="flex flex-wrap items-center gap-2">
        <UInput
          v-model="reason"
          placeholder="Reason, for example “Reviewed with the security team”"
          aria-label="Reason recorded in the baseline"
          maxlength="500"
          class="min-w-0 flex-1 sm:max-w-md"
          :ui="{ base: 'rounded-xs' }"
        />
        <UButton
          type="submit"
          label="Download baseline"
          icon="i-lucide-download"
          color="neutral"
          variant="outline"
          class="rounded-xs"
          :loading="downloading"
        />
      </div>
      <p
        v-if="downloadError"
        class="text-sm text-critical-ink"
      >
        {{ downloadError }}
      </p>
    </form>
  </section>
</template>
