<script setup lang="ts">
import type { ApiToken, CreatedApiToken } from '~~/shared/types/auth'

// Personal API tokens (backend/app/auth/api_tokens.py): the signed-in user's, to create and revoke;
// with userId, that user's on their admin page, to revoke.
const props = defineProps<{ userId?: string }>()
const admin = computed(() => !!props.userId)
const base = computed(() => props.userId ? `/api/admin/users/${props.userId}/tokens` : '/api/account/tokens')

const { data: tokens, refresh, error: loadError } = useFetch<ApiToken[]>(base, { key: `api-tokens-${props.userId ?? 'me'}` })

const EXPIRY_OPTIONS = [
  { label: '30 days', value: 30 },
  { label: '90 days', value: 90 },
  { label: '1 year', value: 365 },
  { label: 'Never', value: 0 }
]
const name = ref('')
const expiresInDays = ref(90)
const creating = ref(false)
const revoking = ref<string | null>(null)
const errorMessage = ref('')
const created = ref<CreatedApiToken | null>(null)
const formOpen = ref(false)
const copied = ref(false)
const copyFailed = ref(false)
const tokenEl = useTemplateRef<HTMLElement>('tokenEl')

async function create() {
  creating.value = true
  errorMessage.value = ''
  copied.value = false
  copyFailed.value = false
  try {
    created.value = await $fetch<CreatedApiToken>('/api/account/tokens', {
      method: 'POST',
      body: { name: name.value.trim(), expiresInDays: expiresInDays.value || null }
    })
    name.value = ''
    formOpen.value = false
    await refresh()
  } catch (err) {
    errorMessage.value = apiErrorMessage(err, 'Couldn’t create the token')
  } finally {
    creating.value = false
  }
}

async function revoke(token: ApiToken) {
  revoking.value = token.id
  errorMessage.value = ''
  try {
    await $fetch(`${base.value}/${token.id}`, { method: 'DELETE' })
    if (created.value?.id === token.id) created.value = null
    await refresh()
  } catch (err) {
    errorMessage.value = apiErrorMessage(err, 'Couldn’t revoke the token')
  } finally {
    revoking.value = null
  }
}

async function copyToken() {
  if (!created.value) return
  try {
    await navigator.clipboard.writeText(created.value.token)
    copied.value = true
  } catch {
    // No clipboard access (e.g. plain HTTP): select it so it can be copied by hand.
    copyFailed.value = true
    if (tokenEl.value) window.getSelection()?.selectAllChildren(tokenEl.value)
  }
}

const expired = (token: ApiToken) => token.expires_at !== null && token.expires_at * 1000 < Date.now()
</script>

<template>
  <UCard :ui="{ root: 'rounded-xs', body: 'p-5 sm:p-6' }">
    <div class="flex flex-col gap-5">
      <div>
        <h2 class="text-lg font-semibold tracking-tight text-highlighted">
          API tokens
        </h2>
        <p class="mt-1 text-sm text-muted">
          <template v-if="admin">
            The tokens this user's scripts and CI jobs scan with. Revoking one stops it working at once.
          </template>
          <template v-else>
            For scripts and CI jobs: a token starts and reads scans as you, with your quotas, and
            nothing else. Send it as <code class="font-mono text-xs">Authorization: Bearer &lt;token&gt;</code>.
          </template>
        </p>
      </div>

      <div
        v-if="created"
        class="flex flex-col gap-2 rounded-xs bg-safe-tint p-4 ring-1 ring-safe-line"
      >
        <p class="text-sm font-semibold text-highlighted">
          Copy “{{ created.name }}” now: it won’t be shown again.
        </p>
        <div class="flex items-center gap-2 rounded-xs bg-default p-2 ring ring-default">
          <code
            ref="tokenEl"
            class="min-w-0 flex-1 truncate px-1 font-mono text-xs text-highlighted"
          >{{ created.token }}</code>
          <UButton
            :icon="copied ? 'i-lucide-check' : 'i-lucide-copy'"
            color="neutral"
            variant="outline"
            size="sm"
            @click="copyToken"
          >
            {{ copied ? 'Copied' : 'Copy' }}
          </UButton>
        </div>
        <p
          v-if="copyFailed"
          class="text-sm text-muted"
        >
          Couldn’t copy it automatically: it’s selected, so copy it by hand.
        </p>
      </div>

      <ul
        v-if="tokens?.length"
        class="flex flex-col divide-y divide-muted border-y border-muted"
      >
        <li
          v-for="token in tokens"
          :key="token.id"
          class="flex flex-wrap items-center gap-x-4 gap-y-1 py-3"
        >
          <div class="flex min-w-0 flex-1 flex-col gap-0.5">
            <span class="font-medium break-words text-highlighted">{{ token.name }}</span>
            <span class="flex flex-wrap gap-x-3 font-mono text-xs text-muted">
              <span>{{ token.prefix }}…</span>
              <span>
                <template v-if="token.last_used_at">used <NuxtTime
                  :datetime="token.last_used_at * 1000"
                  relative
                /></template>
                <template v-else>never used</template>
              </span>
              <span :class="{ 'text-critical-ink': expired(token) }">
                <template v-if="token.expires_at === null">never expires</template>
                <template v-else-if="expired(token)">expired</template>
                <template v-else>expires <NuxtTime
                  :datetime="token.expires_at * 1000"
                  relative
                /></template>
              </span>
            </span>
          </div>
          <UButton
            color="error"
            variant="ghost"
            size="sm"
            :loading="revoking === token.id"
            :aria-label="`Revoke ${token.name}`"
            @click="revoke(token)"
          >
            Revoke
          </UButton>
        </li>
      </ul>
      <p
        v-else-if="tokens"
        class="text-sm text-muted"
      >
        No API tokens{{ admin ? '' : ' yet' }}.
      </p>

      <UButton
        v-if="!admin && !formOpen"
        color="neutral"
        variant="outline"
        icon="i-lucide-plus"
        class="self-start"
        @click="formOpen = true; created = null"
      >
        New token
      </UButton>
      <form
        v-else-if="!admin"
        class="flex flex-wrap items-end gap-3 rounded-xs bg-muted p-4 ring ring-default"
        @submit.prevent="create"
      >
        <UFormField
          label="Name"
          class="min-w-48 flex-1"
        >
          <UInput
            id="api-token-name"
            v-model="name"
            placeholder="e.g. GitHub Actions"
            maxlength="80"
            autofocus
            class="w-full"
          />
        </UFormField>
        <UFormField label="Expires">
          <USelect
            id="api-token-expiry"
            v-model="expiresInDays"
            :items="EXPIRY_OPTIONS"
            class="w-32"
          />
        </UFormField>
        <UButton
          type="submit"
          color="primary"
          icon="i-lucide-plus"
          :loading="creating"
          :disabled="!name.trim()"
        >
          Create token
        </UButton>
        <UButton
          color="neutral"
          variant="ghost"
          @click="formOpen = false; name = ''"
        >
          Cancel
        </UButton>
      </form>

      <UAlert
        v-if="errorMessage || loadError"
        color="error"
        variant="subtle"
        :title="errorMessage || apiErrorMessage(loadError, 'Couldn’t load the tokens')"
      />
    </div>
  </UCard>
</template>
