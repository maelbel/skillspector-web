<script setup lang="ts">
const { session, onSessionChange } = useAuth()
const redirect = useAuthRedirect()

useSeoMeta({ title: 'Create an account — Skillspector Web' })

const email = ref('')
const password = ref('')
const confirm = ref('')
const submitting = ref(false)
const errorMessage = ref('')

const mismatch = computed(() => confirm.value.length > 0 && confirm.value !== password.value)

async function submit() {
  submitting.value = true
  errorMessage.value = ''
  try {
    await $fetch('/api/auth/signup', { method: 'POST', body: { email: email.value.trim(), password: password.value } })
    await onSessionChange()
    await navigateTo(redirect.value)
  } catch (err) {
    errorMessage.value = apiErrorMessage(err, 'Failed to create your account')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <AuthPanel
    eyebrow="Get started"
    title="Create an account"
    :lead="session?.needs_setup
      ? 'No one has an account here yet, so yours becomes the admin of this server.'
      : 'Your scans are private to your account. It takes a few seconds.'"
  >
    <UAlert
      v-if="session && !session.signup_allowed && !session.needs_setup"
      color="neutral"
      variant="subtle"
      icon="i-lucide-user-lock"
      title="Sign-up is closed on this server"
      description="Ask an admin of this server to add you."
    />
    <form
      v-else
      class="flex flex-col gap-4"
      @submit.prevent="submit"
    >
      <UFormField label="Email">
        <UInput
          id="signup-email"
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
        description="At least 10 characters."
      >
        <UInput
          id="signup-password"
          v-model="password"
          type="password"
          autocomplete="new-password"
          size="lg"
          class="w-full"
          required
        />
      </UFormField>
      <UFormField
        label="Confirm password"
        :error="mismatch ? 'The passwords don’t match' : undefined"
      >
        <UInput
          id="signup-confirm"
          v-model="confirm"
          type="password"
          autocomplete="new-password"
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
        :disabled="!email.trim() || password.length < 10 || password !== confirm"
      >
        Create account
      </UButton>
    </form>

    <template #footer>
      <p>
        Already have an account?
        <ULink
          :to="{ path: '/login', query: $route.query }"
          class="font-semibold text-highlighted underline underline-offset-2"
        >
          Sign in
        </ULink>
      </p>
    </template>
  </AuthPanel>
</template>
