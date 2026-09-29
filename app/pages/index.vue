<script setup lang="ts">
useSeoMeta({ title: 'Skillspector Web' })

const { data: health } = useHealth()
const online = computed(() => health.value && health.value.status !== 'down')
</script>

<template>
  <UContainer class="flex flex-col gap-16 pt-8 pb-12 sm:pt-10 lg:gap-24 lg:pt-12">
    <div class="grid items-start gap-12 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)] lg:gap-16">
      <section class="flex flex-col gap-8">
        <div class="flex flex-col items-start gap-5">
          <p
            v-if="health"
            class="flex items-center gap-2 rounded-full border border-default/70 bg-default/60 py-1 pr-3 pl-2 font-mono text-xs text-muted backdrop-blur"
          >
            <span class="relative flex size-2">
              <span
                v-if="online"
                class="absolute inline-flex size-full animate-ping rounded-full bg-matcha-400 opacity-60"
              />
              <span
                class="relative inline-flex size-2 rounded-full"
                :class="online ? 'bg-matcha-500' : 'bg-critical'"
              />
            </span>
            <template v-if="online">
              skillspector {{ health.skillspector_version }} · scanner online
            </template>
            <template v-else>
              scanner offline
            </template>
          </p>
          <h1 class="display text-5xl text-highlighted text-balance sm:text-6xl lg:text-[5.25rem]">
            Is this skill <em class="font-serif font-normal tracking-normal text-primary">safe</em> to install?
          </h1>
          <p class="max-w-xl text-lg text-muted text-pretty">
            Scan a Claude Code, Codex or MCP skill for prompt injection, data exfiltration and
            dangerous code before it runs on your machine.
          </p>
        </div>

        <ScanForm />
      </section>

      <RecentScans class="lg:mt-14" />
    </div>

    <ScanCoverage />
  </UContainer>
</template>
