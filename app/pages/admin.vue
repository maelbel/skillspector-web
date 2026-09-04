<script setup lang="ts">
useSeoMeta({ title: 'Admin — Skillspector Web' })

const adminToken = ref('')
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
  if (!adminToken.value.trim()) return

  starting.value = true
  errorMessage.value = ''

  try {
    const { url } = await $fetch<{ url: string }>('/api/admin/claude-login/start', {
      method: 'POST',
      body: { adminToken: adminToken.value.trim() }
    })
    loginUrl.value = url
    step.value = 'started'
  } catch (err) {
    errorMessage.value = err instanceof Error ? err.message : 'Failed to start login'
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
      { method: 'POST', body: { adminToken: adminToken.value.trim(), code: code.value.trim() } }
    )
    resultSuccess.value = success
    resultMessage.value = output
    step.value = 'done'
  } catch (err) {
    errorMessage.value = err instanceof Error ? err.message : 'Failed to complete login'
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
</script>

<template>
  <UContainer class="py-16">
    <div class="max-w-lg mx-auto flex flex-col gap-6">
      <UButton
        to="/"
        icon="i-lucide-arrow-left"
        variant="ghost"
        color="neutral"
        size="sm"
        class="self-start"
      >
        Back
      </UButton>

      <div>
        <h1 class="text-xl font-bold">
          Claude CLI login
        </h1>
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
            class="flex items-center justify-center size-6 rounded-full text-xs font-semibold shrink-0"
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

      <UCard>
        <div class="flex flex-col gap-4">
          <UFormField
            label="Admin token"
            description="Matches SKILLSPECTOR_WEB_ADMIN_TOKEN on the server."
          >
            <UInput
              v-model="adminToken"
              type="password"
              icon="i-lucide-key-round"
              class="w-full"
              :disabled="step !== 'idle'"
            />
          </UFormField>

          <UButton
            v-if="step === 'idle'"
            icon="i-lucide-play"
            :loading="starting"
            :disabled="!adminToken.trim()"
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
            <pre class="overflow-x-auto rounded-md bg-elevated p-3 text-xs font-mono">{{ resultMessage }}</pre>
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
    </div>
  </UContainer>
</template>
