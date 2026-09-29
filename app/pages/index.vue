<script setup lang="ts">
useSeoMeta({ title: 'Skillspector Web' })
</script>

<template>
  <UContainer class="flex flex-col gap-16 py-12 sm:py-16 lg:gap-20 lg:py-20">
    <div class="grid items-start gap-12 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)] lg:gap-16">
      <section class="flex flex-col gap-7">
        <div class="flex flex-col gap-4">
          <p class="eyebrow text-primary">
            Pre-install check for agent skills
          </p>
          <h1 class="font-serif text-5xl leading-none tracking-tight text-highlighted text-balance sm:text-6xl lg:text-7xl">
            Is this skill safe to install?
          </h1>
          <p class="max-w-xl text-lg text-muted text-pretty">
            Scan a Claude Code, Codex or MCP skill for prompt injection, data exfiltration and
            dangerous code before it runs on your machine.
          </p>
        </div>

        <ScanForm />
      </section>

      <RecentScans class="lg:mt-2" />
    </div>

    <ScanCoverage />
  </UContainer>
</template>
