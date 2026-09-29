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
    class="flex flex-col gap-5"
  >
    <h2
      id="scan-coverage-heading"
      class="eyebrow text-muted"
    >
      What a scan checks
    </h2>

    <ul class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      <li
        v-for="check in CHECKS"
        :key="check.title"
        class="surface flex flex-col gap-2.5 p-5"
      >
        <span class="mb-2 flex size-10 items-center justify-center rounded-full bg-matcha-100 text-matcha-700 dark:bg-matcha-950 dark:text-matcha-300">
          <UIcon
            :name="check.icon"
            class="size-5"
          />
        </span>
        <h3 class="text-base font-semibold tracking-tight text-highlighted">
          {{ check.title }}
        </h3>
        <p class="text-sm text-muted">
          {{ check.description }}
        </p>
      </li>
    </ul>

    <p class="text-sm text-muted">
      Every scan runs more than 20 static analyzers from
      <ULink
        :to="`https://github.com/${site.scannerRepo}`"
        target="_blank"
        class="font-medium text-highlighted underline underline-offset-2"
      >{{ site.scannerRepo }}</ULink>. AI review adds a semantic read of what the skill is trying
      to do.
    </p>
  </section>
</template>
