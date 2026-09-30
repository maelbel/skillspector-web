<script setup lang="ts">
const { accounts, user, session } = useAuth()

useSeoMeta({ title: 'Account — Skillspector Web' })

// There's nothing to manage without accounts.
if (!accounts.value) await navigateTo('/')

const current = ref('')
const next = ref('')
const confirm = ref('')
const saving = ref(false)
const errorMessage = ref('')
const saved = ref(false)

const mismatch = computed(() => confirm.value.length > 0 && confirm.value !== next.value)

async function save() {
  saving.value = true
  errorMessage.value = ''
  saved.value = false
  try {
    await $fetch('/api/auth/password', { method: 'POST', body: { currentPassword: current.value, newPassword: next.value } })
    current.value = ''
    next.value = ''
    confirm.value = ''
    saved.value = true
  } catch (err) {
    errorMessage.value = apiErrorMessage(err, 'Failed to change the password')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <UContainer class="py-12 sm:py-14">
    <div class="mx-auto flex max-w-xl flex-col gap-7">
      <div class="flex flex-col gap-2">
        <h1 class="display text-5xl text-highlighted sm:text-6xl">
          Account
        </h1>
        <p class="text-[15px] text-muted">
          Signed in as <span class="font-semibold text-highlighted">{{ user?.email }}</span>
          <template v-if="user?.role === 'admin'">
            (admin)
          </template>
        </p>
      </div>

      <ClaudeKeyCard v-if="session?.claude_key_available" />
      <UAlert
        v-else-if="user?.role === 'admin'"
        color="neutral"
        variant="subtle"
        icon="i-lucide-key-round"
        title="Saved Claude keys are off on this server"
        description="To let users connect their own Claude key, set SKILLSPECTOR_WEB_SECRET_KEY on the API (generate one with python -m app.secrets_box) and restart it."
      />

      <UCard :ui="{ root: 'rounded-xs', body: 'p-5 sm:p-6' }">
        <form
          class="flex flex-col gap-4"
          @submit.prevent="save"
        >
          <div>
            <h2 class="text-lg font-semibold tracking-tight text-highlighted">
              Change password
            </h2>
            <p class="mt-1 text-sm text-muted">
              You stay signed in here; your other devices are signed out.
            </p>
          </div>
          <UFormField label="Current password">
            <PasswordInput
              id="account-current-password"
              v-model="current"
              autocomplete="current-password"
              class="w-full"
              required
            />
          </UFormField>
          <UFormField
            label="New password"
            description="At least 10 characters."
          >
            <PasswordInput
              id="account-new-password"
              v-model="next"
              autocomplete="new-password"
              class="w-full"
              required
            />
          </UFormField>
          <UFormField
            label="Confirm new password"
            :error="mismatch ? 'The passwords don’t match' : undefined"
          >
            <PasswordInput
              id="account-confirm-password"
              v-model="confirm"
              autocomplete="new-password"
              class="w-full"
              required
            />
          </UFormField>
          <UAlert
            v-if="saved"
            color="success"
            variant="subtle"
            icon="i-lucide-check-circle-2"
            title="Password changed"
          />
          <UAlert
            v-if="errorMessage"
            color="error"
            variant="subtle"
            :title="errorMessage"
          />
          <UButton
            type="submit"
            color="primary"
            icon="i-lucide-key-round"
            class="self-start"
            :loading="saving"
            :disabled="!current || next.length < 10 || next !== confirm"
          >
            Change password
          </UButton>
        </form>
      </UCard>
    </div>
  </UContainer>
</template>
