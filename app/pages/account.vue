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
// The password form opens from its button, and closes once the password is changed.
const changingPassword = ref(false)

function closePasswordForm() {
  changingPassword.value = false
  current.value = ''
  next.value = ''
  confirm.value = ''
  errorMessage.value = ''
}

async function save() {
  saving.value = true
  errorMessage.value = ''
  saved.value = false
  try {
    await $fetch('/api/auth/password', { method: 'POST', body: { currentPassword: current.value, newPassword: next.value } })
    closePasswordForm()
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
    <div class="mx-auto flex max-w-2xl flex-col gap-8">
      <div class="flex flex-col gap-2">
        <h1 class="display text-5xl text-highlighted sm:text-6xl">
          Account
        </h1>
        <p class="flex flex-wrap items-center gap-2 text-[15px] text-muted">
          <span>Signed in as <span class="font-semibold text-highlighted">{{ user?.email }}</span></span>
          <span
            v-if="user?.role === 'admin'"
            class="rounded-xs bg-elevated px-2 py-0.5 text-xs font-semibold text-highlighted ring-1 ring-default"
          >Admin</span>
        </p>
      </div>

      <UsageCard />

      <section
        aria-labelledby="connections-heading"
        class="flex flex-col gap-3"
      >
        <h2
          id="connections-heading"
          class="eyebrow text-muted"
        >
          Connections
        </h2>
        <ClaudeKeyCard v-if="session?.claude_key_available" />
        <UAlert
          v-else-if="user?.role === 'admin'"
          color="neutral"
          variant="subtle"
          icon="i-lucide-key-round"
          title="Saved Claude keys are off on this server"
          description="To let users connect their own Claude key, set SKILLSPECTOR_WEB_SECRET_KEY on the API (generate one with python -m app.secrets_box) and restart it."
        />
        <GitHubConnectionCard />
        <ApiTokensCard />
      </section>

      <section
        aria-labelledby="security-heading"
        class="flex flex-col gap-3"
      >
        <h2
          id="security-heading"
          class="eyebrow text-muted"
        >
          Security
        </h2>
        <UCard :ui="{ root: 'rounded-xs', body: 'p-5 sm:p-6' }">
          <div class="flex flex-col gap-4">
            <div class="flex flex-wrap items-start justify-between gap-3">
              <div class="flex flex-col gap-1">
                <h3 class="text-lg font-semibold tracking-tight text-highlighted">
                  Password
                </h3>
                <p class="text-sm text-muted">
                  Changing it keeps you signed in here, and signs you out everywhere else.
                </p>
              </div>
              <UButton
                v-if="!changingPassword"
                color="neutral"
                variant="outline"
                icon="i-lucide-key-round"
                @click="changingPassword = true; saved = false"
              >
                Change password
              </UButton>
            </div>
            <UAlert
              v-if="saved"
              color="success"
              variant="subtle"
              icon="i-lucide-check-circle-2"
              title="Password changed"
              description="Your other devices are signed out."
            />
            <form
              v-if="changingPassword"
              class="flex flex-col gap-4 rounded-xs bg-muted p-4 ring ring-default"
              @submit.prevent="save"
            >
              <UFormField label="Current password">
                <PasswordInput
                  id="account-current-password"
                  v-model="current"
                  autocomplete="current-password"
                  autofocus
                  class="w-full"
                  required
                />
              </UFormField>
              <div class="grid gap-4 sm:grid-cols-2">
                <UFormField
                  label="New password"
                  hint="10+ characters"
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
                  label="Confirm it"
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
              </div>
              <UAlert
                v-if="errorMessage"
                color="error"
                variant="subtle"
                :title="errorMessage"
              />
              <div class="flex flex-wrap gap-2">
                <UButton
                  type="submit"
                  color="primary"
                  :loading="saving"
                  :disabled="!current || next.length < 10 || next !== confirm"
                >
                  Change password
                </UButton>
                <UButton
                  color="neutral"
                  variant="ghost"
                  @click="closePasswordForm"
                >
                  Cancel
                </UButton>
              </div>
            </form>
          </div>
        </UCard>
      </section>
    </div>
  </UContainer>
</template>
