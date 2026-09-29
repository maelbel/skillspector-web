<script setup lang="ts">
import type { Finding } from '~~/shared/types/scan'

const props = defineProps<{
  finding: Finding
  expanded: boolean
}>()

defineEmits<{
  toggle: []
}>()

const title = computed(() => findingTitle(props.finding))
const location = computed(() => findingLocation(props.finding))
// Snippets often open with blank lines around the match; they only push the code out of view.
const snippet = computed(() => props.finding.code_snippet?.replace(/^\s*\n/, '').trimEnd() ?? '')
// `finding` holds the matched text. Skip it when it just repeats the title or the location.
const matched = computed(() => {
  const text = props.finding.finding?.trim()
  if (!text || text === title.value || text.startsWith(props.finding.location.file)) return undefined
  return text
})
</script>

<template>
  <article class="surface overflow-hidden">
    <button
      type="button"
      :aria-expanded="expanded"
      class="grid w-full cursor-pointer grid-cols-[20px_minmax(0,1fr)] items-start gap-x-3.5 gap-y-2 px-4 py-4 text-left transition-colors hover:bg-muted sm:grid-cols-[20px_minmax(0,1fr)_auto] sm:px-5"
      @click="$emit('toggle')"
    >
      <UIcon
        :name="expanded ? 'i-lucide-chevron-down' : 'i-lucide-chevron-right'"
        class="mt-0.5 size-[18px] text-muted"
      />
      <span class="flex min-w-0 flex-col gap-1.5">
        <span class="text-base font-semibold break-words text-highlighted">{{ title }}</span>
        <span class="flex flex-wrap gap-x-3 gap-y-0.5 font-mono text-xs text-muted">
          <span v-if="finding.category && finding.category !== title">{{ finding.category }}</span>
          <span class="break-all">{{ location }}</span>
        </span>
      </span>
      <span class="flex items-center gap-2.5 max-sm:col-start-2">
        <span class="font-mono text-xs whitespace-nowrap text-muted">{{ Math.round(finding.confidence * 100) }}% sure</span>
        <SeverityBadge :severity="finding.severity" />
      </span>
    </button>

    <div
      v-if="expanded"
      class="flex flex-col gap-4 px-4 pb-5 sm:pr-5 sm:pl-[54px]"
    >
      <p
        v-if="finding.explanation && finding.explanation !== title"
        class="text-[15px] leading-relaxed text-default"
      >
        {{ finding.explanation }}
      </p>

      <p
        v-if="finding.intent"
        class="text-sm text-muted"
      >
        <span class="font-semibold text-highlighted">Likely intent:</span> {{ finding.intent }}
      </p>

      <p
        v-if="matched"
        class="flex min-w-0 flex-col gap-1 text-sm"
      >
        <span class="font-semibold text-highlighted">Matched</span>
        <code class="line-clamp-3 rounded-lg bg-muted px-2.5 py-1.5 font-mono text-xs break-all text-default">{{ matched }}</code>
      </p>

      <figure
        v-if="snippet"
        class="overflow-hidden rounded-2xl bg-code"
      >
        <figcaption class="flex justify-between gap-4 border-b border-white/10 px-4 py-2.5 font-mono text-xs text-oat-400">
          <span class="truncate">{{ finding.location.file }}</span>
          <span
            v-if="finding.location.start_line"
            class="shrink-0"
          >line {{ finding.location.start_line }}</span>
        </figcaption>
        <pre class="max-h-80 overflow-auto p-4 font-mono text-[13px] leading-relaxed text-oat-200">{{ snippet }}</pre>
      </figure>

      <div
        v-if="finding.remediation"
        class="grid grid-cols-[18px_minmax(0,1fr)] gap-2.5 rounded-2xl bg-safe-tint px-4 py-3.5 ring-1 ring-safe-line"
      >
        <UIcon
          name="i-lucide-check"
          class="mt-0.5 size-[18px] text-safe-ink"
        />
        <div class="flex flex-col gap-1 text-sm">
          <span class="font-semibold text-safe-ink">How to fix</span>
          <span class="leading-relaxed text-highlighted">{{ finding.remediation }}</span>
        </div>
      </div>

      <ul
        v-if="finding.tags.length"
        class="flex flex-wrap gap-1.5"
      >
        <li
          v-for="tag in finding.tags"
          :key="tag"
          class="rounded-full border border-default px-2 py-0.5 font-mono text-[11px] text-muted"
        >
          {{ tag }}
        </li>
      </ul>
    </div>
  </article>
</template>
