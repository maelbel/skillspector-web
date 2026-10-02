<script setup lang="ts">
import type { Health } from '~~/shared/types/backoffice'

// The backoffice's health panel: the last day's failures, the last error, and where alerts go
// (backend/app/monitoring.py); the monitoring page has the rest.
const props = defineProps<{ health: Health }>()

const RULES: Record<string, string> = {
  sandbox_error: 'sandbox error',
  failure_rate: 'many scans failing',
  queue_redeliveries: 'queue redeliveries',
  bot_refusals: 'every submission refused'
}

const state = computed(() => {
  const health = props.health
  if (health.sandbox_errors) return { label: 'Scans can’t run', dot: 'bg-critical' }
  if (health.failed && health.failed * 2 >= health.finished) return { label: 'Many scans failing', dot: 'bg-critical' }
  if (health.failed || health.redeliveries) return { label: 'Some scans failed', dot: 'bg-medium' }
  return { label: 'No problems', dot: 'bg-safe' }
})

const tiles = computed(() => {
  const health = props.health
  return [
    { label: 'Failed scans', value: health.failed, note: `of ${health.finished} finished`, show: true },
    { label: 'Sandbox errors', value: health.sandbox_errors, note: null, show: true },
    { label: 'Queue redeliveries', value: health.redeliveries, note: null, show: health.redeliveries > 0 },
    { label: 'Refused as bots', value: health.bot_refusals, note: null, show: health.bot_refusals > 0 }
  ].filter(tile => tile.show)
})

const channelText = computed(() => props.health.alert_channels.map(channel => channel === 'webhook' ? 'the webhook' : 'email').join(' and '))
</script>

<template>
  <section
    aria-labelledby="health-heading"
    class="surface flex flex-col gap-4 p-5 sm:p-6"
  >
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h2
        id="health-heading"
        class="text-lg font-semibold tracking-tight text-highlighted"
      >
        Health
        <span class="text-sm font-normal text-muted">· last {{ health.hours }} hours</span>
      </h2>
      <span class="flex items-center gap-2 text-sm font-semibold text-highlighted">
        <span
          class="size-2"
          :class="state.dot"
        />
        {{ state.label }}
      </span>
    </div>

    <div class="grid grid-cols-2 gap-4 sm:grid-cols-4">
      <div
        v-for="tile in tiles"
        :key="tile.label"
        class="flex flex-col gap-1"
      >
        <span class="text-sm text-muted">{{ tile.label }}</span>
        <span class="font-mono text-2xl font-semibold text-highlighted tabular-nums">{{ tile.value }}</span>
        <span
          v-if="tile.note"
          class="text-xs text-dimmed"
        >{{ tile.note }}</span>
      </div>
    </div>

    <div
      v-if="health.last_error"
      class="flex flex-col gap-1 rounded-xs bg-muted p-3 ring ring-default"
    >
      <span class="flex flex-wrap items-center gap-x-2 text-xs text-muted">
        <span class="font-semibold">{{ health.last_error.kind === 'sandbox_error' ? 'Last sandbox error' : 'Last failed scan' }}</span>
        <span :title="formatDate(health.last_error.at)">
          <NuxtTime
            :datetime="health.last_error.at * 1000"
            relative
          />
        </span>
        <NuxtLink
          v-if="health.last_error.scan_id"
          :to="`/scan/${health.last_error.scan_id}`"
          class="underline-offset-2 hover:underline"
        >View scan</NuxtLink>
      </span>
      <code class="font-mono text-xs break-words whitespace-pre-wrap text-highlighted">{{ health.last_error.message || 'No message' }}</code>
    </div>

    <div class="flex flex-wrap items-center justify-between gap-3 border-t border-default pt-4">
      <p
        v-if="health.alert_channels.length"
        class="text-sm text-muted"
      >
        Alerts go to {{ channelText }}.
        <template v-if="health.last_alert">
          The last one, {{ RULES[health.last_alert.rule ?? ''] ?? health.last_alert.rule }},
          <NuxtTime
            :datetime="health.last_alert.at * 1000"
            relative
          />.
        </template>
      </p>
      <p
        v-else
        class="text-sm text-muted"
      >
        Alerts aren’t set up: set <code class="font-mono text-xs">SKILLSPECTOR_WEB_ALERT_WEBHOOK_URL</code> or
        <code class="font-mono text-xs">SKILLSPECTOR_WEB_ALERT_EMAIL</code> to hear about failures as they happen.
      </p>
      <ULink
        to="/admin/monitoring"
        class="text-sm font-semibold text-brand-ink"
      >
        Monitoring →
      </ULink>
    </div>
  </section>
</template>
