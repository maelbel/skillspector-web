<script setup lang="ts">
useSeoMeta({ title: 'Skillspector Web' })
</script>

<template>
  <UContainer class="py-16 sm:py-24">
    <div class="max-w-xl mx-auto flex flex-col gap-8">
      <div class="text-center flex flex-col items-center gap-4">
        <div class="flex items-center justify-center size-14 rounded-full bg-primary/10">
          <UIcon
            name="i-lucide-shield-check"
            class="size-7 text-primary"
          />
        </div>
        <div>
          <h1 class="text-3xl font-bold tracking-tight">
            Is this skill safe to install?
          </h1>
          <p class="mt-3 text-muted text-balance">
            Scan an AI agent skill (Claude Code, Codex, MCP) for prompt injection, data
            exfiltration, and other vulnerabilities before you install it.
          </p>
        </div>
      </div>

      <ScanForm />
    </div>
  </UContainer>
</template>
