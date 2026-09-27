<script setup lang="ts">
const { site } = useAppConfig()

// Grouped from skillspector's analyzer nodes (static_patterns_*, static_yara, behavioral_*,
// mcp_*, artifact_integrity), so the copy stays true to what a scan actually runs.
const CHECKS = [
  {
    icon: 'i-lucide-message-square-warning',
    title: 'Prompt injection',
    description: 'Hidden instructions, anti-refusal tricks, system-prompt leaks and memory poisoning.'
  },
  {
    icon: 'i-lucide-send',
    title: 'Data exfiltration',
    description: 'Reading secrets or agent data and sending it elsewhere, including server-side requests.'
  },
  {
    icon: 'i-lucide-terminal',
    title: 'Dangerous code',
    description: 'Privilege escalation, tool misuse, unsafe deserialization, malware signatures and code-flow analysis.'
  },
  {
    icon: 'i-lucide-package-search',
    title: 'Supply chain & MCP',
    description: 'Tampered artifacts, risky dependencies, and MCP tools that are poisoned, over-privileged or change later.'
  }
]
</script>

<template>
  <section
    aria-labelledby="scan-coverage-heading"
    class="flex flex-col gap-3"
  >
    <h2
      id="scan-coverage-heading"
      class="text-sm font-semibold text-highlighted"
    >
      What a scan checks
    </h2>

    <ul class="grid gap-3 sm:grid-cols-2">
      <li
        v-for="check in CHECKS"
        :key="check.title"
        class="flex gap-3 rounded-lg border border-default p-4"
      >
        <UIcon
          :name="check.icon"
          class="size-5 shrink-0 text-primary mt-0.5"
        />
        <div>
          <p class="text-sm font-medium text-highlighted">
            {{ check.title }}
          </p>
          <p class="mt-1 text-xs text-muted">
            {{ check.description }}
          </p>
        </div>
      </li>
    </ul>

    <p class="text-xs text-muted">
      Every scan runs more than 20 static analyzers from
      <ULink
        :to="`https://github.com/${site.scannerRepo}`"
        target="_blank"
        class="underline"
      >{{ site.scannerRepo }}</ULink>. Deep analysis adds an AI review of what the skill is trying
      to do.
    </p>
  </section>
</template>
