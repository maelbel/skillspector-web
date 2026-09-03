<script setup lang="ts">
useSeoMeta({ title: 'Skillspector Web' })
</script>

<template>
  <UContainer class="py-16">
    <div class="max-w-xl mx-auto flex flex-col gap-6">
      <div class="text-center">
        <h1 class="text-2xl font-bold">
          Is this skill safe to install?
        </h1>
        <p class="mt-2 text-muted">
          Scan an AI agent skill (Claude Code, Codex, MCP) for prompt injection, data
          exfiltration, and other vulnerabilities before you install it.
        </p>
      </div>

      <ScanForm />
    </div>
  </UContainer>
</template>
