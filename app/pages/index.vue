<script setup lang="ts">
useSeoMeta({ title: 'Skillspector Web' })

// With accounts on, signed-out visitors get the landing page instead of the scanner.
const { accounts, user } = useAuth()
const { data: health } = useHealth()
const online = computed(() => health.value && health.value.status !== 'down')
</script>

<template>
  <LandingPage v-if="accounts && !user" />
  <UContainer
    v-else
    class="flex flex-col gap-16 pt-8 pb-12 sm:pt-10 lg:gap-24 lg:pt-12"
  >
    <!-- Side by side, the recent scans end where the form does. -->
    <div class="grid items-start gap-12 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)] lg:items-end lg:gap-16">
      <section class="flex flex-col gap-8">
        <div class="flex flex-col items-start gap-5">
          <p
            v-if="health"
            class="flex items-center gap-2 border-l-[3px] border-brand bg-default py-1.5 pr-3 pl-2.5 font-mono text-xs text-muted"
          >
            <span class="relative flex size-2">
              <span
                v-if="online"
                class="absolute inline-flex size-full animate-ping rounded-xs bg-nv-400 opacity-60"
              />
              <span
                class="relative inline-flex size-2 rounded-xs"
                :class="online ? 'bg-nv-500' : 'bg-critical'"
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
            Is this skill <span class="text-brand-ink">safe</span> to install?
          </h1>
          <p class="max-w-xl text-lg text-muted text-pretty">
            Scan a Claude Code, Codex or MCP skill for prompt injection, data exfiltration and
            dangerous code before it runs on your machine.
          </p>
        </div>

        <ScanForm />
      </section>

      <RecentScans />
    </div>

    <ScanCoverage />
  </UContainer>
</template>
