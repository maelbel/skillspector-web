<script setup lang="ts">
import type { SettingsResponse } from '~~/shared/types/settings'

useSeoMeta({ title: 'Admin — Skillspector Web' })

const { accounts, session } = useAuth()

useSeoMeta({ title: 'Settings — Backoffice — Skillspector Web' })

const step = ref<'idle' | 'started' | 'done'>('idle')
const loginUrl = ref('')
const code = ref('')
const starting = ref(false)
const completing = ref(false)
const errorMessage = ref('')
const resultMessage = ref('')
const resultSuccess = ref(false)

const stepNumber = computed(() => ({ idle: 1, started: 2, done: 3 })[step.value])

async function startLogin() {
  starting.value = true
  errorMessage.value = ''

  try {
    const { url } = await $fetch<{ url: string }>('/api/admin/claude-login/start', { method: 'POST' })
    loginUrl.value = url
    step.value = 'started'
  } catch (err) {
    errorMessage.value = apiErrorMessage(err, 'Failed to start login')
  } finally {
    starting.value = false
  }
}

async function completeLogin() {
  if (!code.value.trim()) return

  completing.value = true
  errorMessage.value = ''

  try {
    const { success, output } = await $fetch<{ success: boolean, output: string }>(
      '/api/admin/claude-login/complete',
      { method: 'POST', body: { code: code.value.trim() } }
    )
    resultSuccess.value = success
    resultMessage.value = output
    step.value = 'done'
  } catch (err) {
    errorMessage.value = apiErrorMessage(err, 'Failed to complete login')
  } finally {
    completing.value = false
  }
}

function reset() {
  step.value = 'idle'
  loginUrl.value = ''
  code.value = ''
  errorMessage.value = ''
  resultMessage.value = ''
}

const { data: settingsData } = await useFetch<SettingsResponse>('/api/settings')

const retentionMode = ref<'forever' | 'days'>('forever')
const retentionDays = ref(30)
const savingRetention = ref(false)
const retentionError = ref('')
const retentionSaved = ref(false)

watch(settingsData, (value) => {
  if (!value) return
  if (value.scan_retention_days === null) {
    retentionMode.value = 'forever'
  } else {
    retentionMode.value = 'days'
    retentionDays.value = value.scan_retention_days
  }
}, { immediate: true })

const savingSignup = ref(false)
const signupError = ref('')

async function setSignup(allowSignup: boolean) {
  savingSignup.value = true
  signupError.value = ''
  try {
    settingsData.value = await $fetch<SettingsResponse>('/api/settings', { method: 'PUT', body: { allowSignup } })
    await refreshNuxtData('auth-session')
  } catch (err) {
    signupError.value = apiErrorMessage(err, 'Failed to save')
  } finally {
    savingSignup.value = false
  }
}

async function saveRetention() {
  savingRetention.value = true
  retentionError.value = ''
  retentionSaved.value = false

  try {
    const updated = await $fetch<SettingsResponse>('/api/settings', {
      method: 'PUT',
      body: {
        scanRetentionDays: retentionMode.value === 'forever' ? null : retentionDays.value
      }
    })
    settingsData.value = updated
    retentionSaved.value = true
  } catch (err) {
    retentionError.value = apiErrorMessage(err, 'Failed to save')
  } finally {
    savingRetention.value = false
  }
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <BackofficeHeader
      title="Settings"
      lead="How this server runs: accounts, email, the Claude login and scan retention."
    />

    <div class="flex max-w-2xl flex-col gap-6">
      <NoAuthWarning v-if="!accounts" />

      <UCard
        v-else
        :ui="{ root: 'rounded-xs', body: 'p-5 sm:p-6' }"
      >
        <div class="flex flex-col gap-4">
          <div>
            <h2 class="text-lg font-semibold tracking-tight text-highlighted">
              Sign-up
            </h2>
            <p class="mt-1 text-sm text-muted">
              Whether visitors can create their own account from the landing page. When it's off,
              admins add users from the Users page.
            </p>
          </div>
          <USwitch
            :model-value="settingsData?.allow_signup ?? false"
            :loading="savingSignup"
            label="Visitors can create an account"
            @update:model-value="setSignup"
          />
          <UAlert
            v-if="signupError"
            color="error"
            variant="subtle"
            :title="signupError"
          />
        </div>
      </UCard>

      <UCard
        v-if="accounts"
        :ui="{ root: 'rounded-xs', body: 'p-5 sm:p-6' }"
      >
        <div class="flex flex-col gap-3">
          <div class="flex items-center justify-between gap-3">
            <h2 class="text-lg font-semibold tracking-tight text-highlighted">
              Email
            </h2>
            <span
              class="inline-flex items-center gap-1.5 px-2 py-1 text-xs font-semibold"
              :class="session?.email_enabled ? 'bg-safe-tint text-safe-ink' : 'bg-elevated text-muted'"
            >
              <UIcon
                :name="session?.email_enabled ? 'i-lucide-mail-check' : 'i-lucide-mail-x'"
                class="size-3.5"
              />
              {{ session?.email_enabled ? 'Sending' : 'Not configured' }}
            </span>
          </div>
          <p class="text-sm text-muted">
            <template v-if="session?.email_enabled">
              Users can reset a forgotten password by email from the sign-in page, and you can email
              them a reset link from their page.
            </template>
            <template v-else>
              Without email, forgotten passwords go through reset links you copy from a user's page.
              To send reset emails, set these on the API and restart it:
            </template>
          </p>
          <pre
            v-if="!session?.email_enabled"
            class="overflow-x-auto bg-muted p-3 font-mono text-xs text-highlighted"
          >SKILLSPECTOR_WEB_SMTP_HOST=smtp.example.com
SKILLSPECTOR_WEB_SMTP_PORT=587
SKILLSPECTOR_WEB_SMTP_USERNAME=…
SKILLSPECTOR_WEB_SMTP_PASSWORD=…
SKILLSPECTOR_WEB_MAIL_FROM=Skillspector &lt;noreply@example.com&gt;
SKILLSPECTOR_WEB_PUBLIC_URL=https://skillspector.example.com</pre>
        </div>
      </UCard>

      <UCard :ui="{ root: 'rounded-xs', body: 'p-5 sm:p-6' }">
        <div class="flex flex-col gap-4">
          <div>
            <h2 class="text-lg font-semibold tracking-tight text-highlighted">
              Claude CLI login
            </h2>
            <p class="mt-1 text-sm text-muted">
              Re-authenticates the server-wide login every visitor's Claude CLI scans share.
            </p>
          </div>

          <div class="flex items-center gap-2">
            <template
              v-for="n in 3"
              :key="n"
            >
              <div
                class="flex items-center justify-center size-6 rounded-xs text-xs font-semibold shrink-0"
                :class="n <= stepNumber ? 'bg-primary text-inverted' : 'bg-elevated text-muted'"
              >
                {{ n }}
              </div>
              <div
                v-if="n < 3"
                class="h-px flex-1"
                :class="n < stepNumber ? 'bg-primary' : 'bg-default'"
              />
            </template>
          </div>

          <UButton
            v-if="step === 'idle'"
            icon="i-lucide-play"
            :loading="starting"
            @click="startLogin"
          >
            Start login
          </UButton>

          <template v-if="step === 'started'">
            <UAlert
              color="primary"
              variant="subtle"
              icon="i-lucide-external-link"
              title="Visit this link to sign in"
              :description="loginUrl"
            />
            <UButton
              :to="loginUrl"
              target="_blank"
              variant="outline"
              icon="i-lucide-external-link"
            >
              Open login page
            </UButton>

            <UFormField
              label="Code"
              description="Paste the code Anthropic shows you after signing in."
            >
              <UInput
                id="claude-login-code"
                v-model="code"
                icon="i-lucide-clipboard-paste"
                class="w-full"
              />
            </UFormField>

            <UButton
              icon="i-lucide-check"
              :loading="completing"
              :disabled="!code.trim()"
              @click="completeLogin"
            >
              Complete login
            </UButton>
          </template>

          <template v-if="step === 'done'">
            <UAlert
              :color="resultSuccess ? 'primary' : 'error'"
              variant="subtle"
              :icon="resultSuccess ? 'i-lucide-check-circle-2' : 'i-lucide-circle-x'"
              :title="resultSuccess ? 'Logged in' : 'Login failed'"
            />
            <pre class="overflow-x-auto rounded-xs bg-elevated p-3 text-xs font-mono">{{ resultMessage }}</pre>
            <UButton
              variant="outline"
              icon="i-lucide-rotate-ccw"
              @click="reset"
            >
              Start over
            </UButton>
          </template>

          <UAlert
            v-if="errorMessage"
            color="error"
            variant="subtle"
            :title="errorMessage"
          />
        </div>
      </UCard>

      <UCard :ui="{ root: 'rounded-xs', body: 'p-5 sm:p-6' }">
        <div class="flex flex-col gap-4">
          <div>
            <h2 class="text-lg font-semibold tracking-tight text-highlighted">
              Scan retention
            </h2>
            <p class="mt-1 text-sm text-muted">
              Automatically delete scans from history after a set number of days.
            </p>
          </div>

          <UFormField label="Keep scans">
            <USelect
              id="retention-mode"
              v-model="retentionMode"
              :items="[
                { label: 'Forever', value: 'forever' },
                { label: 'For a set number of days', value: 'days' }
              ]"
              value-key="value"
              class="w-full"
            />
          </UFormField>

          <UFormField
            v-if="retentionMode === 'days'"
            label="Days"
          >
            <UInput
              id="retention-days"
              v-model.number="retentionDays"
              type="number"
              min="1"
              step="1"
              class="w-full"
            />
          </UFormField>

          <UButton
            icon="i-lucide-save"
            :loading="savingRetention"
            :disabled="retentionMode === 'days' && (!retentionDays || retentionDays <= 0)"
            @click="saveRetention"
          >
            Save
          </UButton>

          <UAlert
            v-if="retentionSaved"
            color="primary"
            variant="subtle"
            icon="i-lucide-check-circle-2"
            title="Saved"
          />
          <UAlert
            v-if="retentionError"
            color="error"
            variant="subtle"
            :title="retentionError"
          />
        </div>
      </UCard>
    </div>
  </div>
</template>
