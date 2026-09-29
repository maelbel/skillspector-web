<script setup lang="ts">
const route = useRoute()
const { session, onSessionChange } = useAuth()

useSeoMeta({ title: 'Sign in — Skillspector Web' })

type Step = 'setup' | 'signin' | 'signup'
const step = ref<Step>(session.value?.needs_setup ? 'setup' : 'signin')
watch(() => session.value?.needs_setup, (needsSetup) => {
  if (needsSetup) step.value = 'setup'
})

const COPY: Record<Step, { title: string, lead: string, action: string, endpoint: string }> = {
  setup: {
    title: 'Create the admin account',
    lead: 'This server has accounts turned on and no one has signed up yet. The first account becomes the admin.',
    action: 'Create admin account',
    endpoint: '/api/auth/setup'
  },
  signin: {
    title: 'Sign in',
    lead: 'Sign in to scan skills and see your scan history.',
    action: 'Sign in',
    endpoint: '/api/auth/login'
  },
  signup: {
    title: 'Create an account',
    lead: 'Your scans are private to your account.',
    action: 'Create account',
    endpoint: '/api/auth/signup'
  }
}
const copy = computed(() => COPY[step.value])

const email = ref('')
const password = ref('')
const submitting = ref(false)
const errorMessage = ref('')

async function submit() {
  submitting.value = true
  errorMessage.value = ''
  try {
    await $fetch(copy.value.endpoint, { method: 'POST', body: { email: email.value.trim(), password: password.value } })
    await onSessionChange()
    const redirect = typeof route.query.redirect === 'string' && route.query.redirect.startsWith('/') ? route.query.redirect : '/'
    await navigateTo(redirect)
  } catch (err) {
    errorMessage.value = apiErrorMessage(err, 'Something went wrong')
  } finally {
    submitting.value = false
  }
}

function switchTo(next: Step) {
  step.value = next
  errorMessage.value = ''
}
</script>

<template>
  <UContainer class="py-16 sm:py-24">
    <div class="mx-auto flex max-w-md flex-col gap-7">
      <div class="flex flex-col gap-3">
        <p class="eyebrow text-brand-ink">
          {{ step === 'setup' ? 'First run' : 'Skillspector Web' }}
        </p>
        <h1 class="display text-4xl text-highlighted sm:text-5xl">
          {{ copy.title }}
        </h1>
        <p class="text-[15px] text-muted">
          {{ copy.lead }}
        </p>
      </div>

      <form
        class="surface flex flex-col gap-4 border-t-[3px] border-t-brand p-5 sm:p-6"
        @submit.prevent="submit"
      >
        <UFormField label="Email">
          <UInput
            id="login-email"
            v-model="email"
            type="email"
            autocomplete="email"
            size="lg"
            class="w-full"
            required
            autofocus
          />
        </UFormField>
        <UFormField
          label="Password"
          :description="step === 'signin' ? undefined : 'At least 10 characters.'"
        >
          <UInput
            id="login-password"
            v-model="password"
            type="password"
            :autocomplete="step === 'signin' ? 'current-password' : 'new-password'"
            size="lg"
            class="w-full"
            required
          />
        </UFormField>

        <UAlert
          v-if="errorMessage"
          color="error"
          variant="subtle"
          icon="i-lucide-circle-alert"
          :title="errorMessage"
        />

        <UButton
          type="submit"
          color="primary"
          size="lg"
          block
          :loading="submitting"
          :disabled="!email.trim() || !password"
        >
          {{ copy.action }}
        </UButton>
      </form>

      <p
        v-if="step === 'signin' && session?.signup_allowed"
        class="text-sm text-muted"
      >
        New here?
        <button
          type="button"
          class="cursor-pointer font-semibold text-highlighted underline underline-offset-2"
          @click="switchTo('signup')"
        >
          Create an account
        </button>
      </p>
      <p
        v-else-if="step === 'signup'"
        class="text-sm text-muted"
      >
        Already have an account?
        <button
          type="button"
          class="cursor-pointer font-semibold text-highlighted underline underline-offset-2"
          @click="switchTo('signin')"
        >
          Sign in
        </button>
      </p>
      <p
        v-else-if="step === 'signin'"
        class="text-sm text-muted"
      >
        No account? Ask an admin of this server to add you.
      </p>
    </div>
  </UContainer>
</template>
