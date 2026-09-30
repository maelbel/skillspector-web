<script setup lang="ts">
const { session } = useAuth()

const STEPS = [
  { icon: 'i-lucide-link', title: 'Paste a link', text: 'A GitHub, GitLab, Bitbucket or Hugging Face repository, or a single SKILL.md.' },
  { icon: 'i-lucide-scan-eye', title: 'We inspect it', text: 'More than 20 analyzers read the skill for hidden instructions, exfiltration and dangerous code.' },
  { icon: 'i-lucide-shield-check', title: 'Get a verdict', text: 'Safe, review first, or do not install, with every finding explained and a fix suggested.' }
]
</script>

<template>
  <div class="flex flex-col gap-20 pt-12 pb-8 sm:pt-16 lg:gap-24">
    <UContainer>
      <section class="flex max-w-3xl flex-col items-start gap-6">
        <p class="flex items-center gap-2 border-l-[3px] border-brand bg-default py-1.5 pr-3 pl-2.5 font-mono text-xs text-muted">
          Pre-install security check for agent skills
        </p>
        <h1 class="display text-5xl text-highlighted text-balance sm:text-6xl lg:text-[5.25rem]">
          Is this skill <span class="text-brand-ink">safe</span> to install?
        </h1>
        <p class="max-w-2xl text-lg text-muted text-pretty">
          Scan a Claude Code, Codex or MCP skill for prompt injection, data exfiltration and dangerous
          code before it runs on your machine. Your scans stay private to your account.
        </p>
        <div class="flex flex-wrap gap-3">
          <UButton
            v-if="session?.signup_allowed"
            to="/signup"
            color="primary"
            size="xl"
            trailing-icon="i-lucide-arrow-right"
          >
            Create an account
          </UButton>
          <UButton
            to="/login"
            :color="session?.signup_allowed ? 'neutral' : 'primary'"
            :variant="session?.signup_allowed ? 'outline' : 'solid'"
            size="xl"
          >
            Sign in
          </UButton>
        </div>
      </section>
    </UContainer>

    <UContainer>
      <section
        aria-labelledby="how-heading"
        class="flex flex-col gap-5"
      >
        <h2
          id="how-heading"
          class="eyebrow text-muted"
        >
          How it works
        </h2>
        <ol class="grid gap-3 md:grid-cols-3">
          <li
            v-for="(step, index) in STEPS"
            :key="step.title"
            class="surface flex flex-col gap-3 p-6"
          >
            <span class="flex items-center gap-3">
              <span class="flex size-10 items-center justify-center bg-black text-brand">
                <UIcon
                  :name="step.icon"
                  class="size-5"
                />
              </span>
              <span class="font-mono text-sm text-dimmed">0{{ index + 1 }}</span>
            </span>
            <h3 class="text-lg font-semibold tracking-tight text-highlighted">
              {{ step.title }}
            </h3>
            <p class="text-sm text-muted">
              {{ step.text }}
            </p>
          </li>
        </ol>
      </section>
    </UContainer>

    <UContainer>
      <ScanCoverage />
    </UContainer>
  </div>
</template>
