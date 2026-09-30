<script setup lang="ts">
import type { User, UserRole } from '~~/shared/types/auth'

const { user: me } = useAuth()
const { data: users, error, refresh } = await useFetch<User[]>('/api/admin/users', { key: 'admin-users' })

const email = ref('')
const password = ref('')
const role = ref<UserRole>('user')
const adding = ref(false)
const addError = ref('')

async function addUser() {
  adding.value = true
  addError.value = ''
  try {
    await $fetch('/api/admin/users', {
      method: 'POST',
      body: { email: email.value.trim(), password: password.value, role: role.value }
    })
    email.value = ''
    password.value = ''
    role.value = 'user'
    await refresh()
  } catch (err) {
    addError.value = apiErrorMessage(err, 'Failed to add the user')
  } finally {
    adding.value = false
  }
}

const removing = ref<User | null>(null)
const removeError = ref('')

// A one-time link the admin passes on to the user: there's no email on this server.
const resetFor = ref<User | null>(null)
const resetLink = ref<{ url: string, expiresAt: number } | null>(null)
const resetError = ref('')
const copied = ref(false)
const copyFailed = ref(false)
const resetLinkEl = useTemplateRef<HTMLElement>('resetLinkEl')

async function createResetLink(user: User) {
  resetFor.value = user
  resetLink.value = null
  resetError.value = ''
  copied.value = false
  copyFailed.value = false
  try {
    resetLink.value = await $fetch<{ url: string, expiresAt: number }>(`/api/admin/users/${user.id}/reset`, { method: 'POST' })
  } catch (err) {
    resetError.value = apiErrorMessage(err, 'Failed to create a reset link')
  }
}

async function copyResetLink() {
  if (!resetLink.value) return
  try {
    await navigator.clipboard.writeText(resetLink.value.url)
    copied.value = true
  } catch {
    // No clipboard access (e.g. plain HTTP): select the link so it can be copied by hand.
    copyFailed.value = true
    const el = resetLinkEl.value
    if (el) window.getSelection()?.selectAllChildren(el)
  }
}

async function confirmRemove() {
  if (!removing.value) return
  removeError.value = ''
  try {
    await $fetch(`/api/admin/users/${removing.value.id}`, { method: 'DELETE' })
    removing.value = null
    await refresh()
  } catch (err) {
    removeError.value = apiErrorMessage(err, 'Failed to remove the user')
  }
}
</script>

<template>
  <UCard :ui="{ root: 'rounded-xs', body: 'p-5 sm:p-6' }">
    <div class="flex flex-col gap-5">
      <div>
        <h2 class="text-lg font-semibold tracking-tight text-highlighted">
          Users
        </h2>
        <p class="mt-1 text-sm text-muted">
          Everyone who can sign in. Users see only their own scans; admins see every scan and manage
          this page.
        </p>
      </div>

      <UAlert
        v-if="error"
        color="error"
        variant="subtle"
        :title="apiErrorMessage(error, 'Failed to load users')"
      />

      <ul
        v-else-if="users?.length"
        class="divide-y divide-default border-y border-default"
      >
        <li
          v-for="user in users"
          :key="user.id"
          class="flex items-center justify-between gap-3 py-3"
        >
          <div class="min-w-0">
            <p class="truncate text-sm font-semibold text-highlighted">
              {{ user.email }}
              <span
                v-if="user.id === me?.id"
                class="font-normal text-muted"
              >(you)</span>
            </p>
            <p class="font-mono text-xs text-dimmed">
              {{ user.role }}
            </p>
          </div>
          <div
            v-if="user.id !== me?.id"
            class="flex shrink-0 items-center"
          >
            <UButton
              icon="i-lucide-key-round"
              color="neutral"
              variant="ghost"
              :aria-label="`Create a password reset link for ${user.email}`"
              class="size-10 justify-center text-dimmed hover:text-highlighted"
              @click="createResetLink(user)"
            />
            <UButton
              icon="i-lucide-trash-2"
              color="neutral"
              variant="ghost"
              :aria-label="`Remove ${user.email}`"
              class="size-10 justify-center text-dimmed hover:text-critical-ink"
              @click="removing = user; removeError = ''"
            />
          </div>
        </li>
      </ul>

      <form
        class="flex flex-col gap-3"
        @submit.prevent="addUser"
      >
        <p class="text-sm font-semibold text-highlighted">
          Add a user
        </p>
        <div class="grid gap-3 sm:grid-cols-2">
          <UFormField label="Email">
            <UInput
              id="new-user-email"
              v-model="email"
              type="email"
              autocomplete="off"
              class="w-full"
              required
            />
          </UFormField>
          <UFormField
            label="Password"
            description="At least 10 characters. Share it with them securely."
          >
            <UInput
              id="new-user-password"
              v-model="password"
              type="password"
              autocomplete="new-password"
              class="w-full"
              required
            />
          </UFormField>
        </div>
        <UFormField label="Role">
          <USelect
            id="new-user-role"
            v-model="role"
            :items="[{ label: 'User — runs and sees their own scans', value: 'user' }, { label: 'Admin — everything, including this page', value: 'admin' }]"
            value-key="value"
            class="w-full"
          />
        </UFormField>
        <UAlert
          v-if="addError"
          color="error"
          variant="subtle"
          :title="addError"
        />
        <UButton
          type="submit"
          color="primary"
          icon="i-lucide-user-plus"
          class="self-start"
          :loading="adding"
          :disabled="!email.trim() || password.length < 10"
        >
          Add user
        </UButton>
      </form>
    </div>

    <UModal
      :open="!!resetFor"
      title="Password reset link"
      :description="`Send this to ${resetFor?.email ?? 'them'} yourself. It works once, for 24 hours, and cancels any earlier link.`"
      @update:open="(value) => { if (!value) resetFor = null }"
    >
      <template #body>
        <div class="flex flex-col gap-3">
          <UAlert
            v-if="resetError"
            color="error"
            variant="subtle"
            :title="resetError"
          />
          <template v-else-if="resetLink">
            <code
              ref="resetLinkEl"
              class="block rounded-xs bg-muted p-3 font-mono text-xs break-all text-highlighted select-all"
            >{{ resetLink.url }}</code>
            <p
              v-if="copyFailed"
              class="text-xs text-warning"
            >
              Couldn’t copy automatically: the link is selected, copy it with Ctrl+C or ⌘C.
            </p>
            <p class="text-xs text-muted">
              Expires <NuxtTime
                :datetime="resetLink.expiresAt * 1000"
                relative
              />.
            </p>
          </template>
          <p
            v-else
            class="text-sm text-muted"
          >
            Creating the link…
          </p>
        </div>
      </template>
      <template #footer>
        <div class="flex w-full justify-end gap-2">
          <UButton
            variant="ghost"
            color="neutral"
            @click="resetFor = null"
          >
            Done
          </UButton>
          <UButton
            v-if="resetLink"
            color="primary"
            :icon="copied ? 'i-lucide-check' : 'i-lucide-copy'"
            @click="copyResetLink"
          >
            {{ copied ? 'Copied' : 'Copy link' }}
          </UButton>
        </div>
      </template>
    </UModal>

    <UModal
      :open="!!removing"
      title="Remove user"
      description="They're signed out and can't sign in again. Their scans stay, visible to admins."
      @update:open="(value) => { if (!value) removing = null }"
    >
      <template #body>
        <div class="flex flex-col gap-4">
          <p class="font-mono text-sm break-all text-muted">
            {{ removing?.email }}
          </p>
          <UAlert
            v-if="removeError"
            color="error"
            variant="subtle"
            :title="removeError"
          />
        </div>
      </template>
      <template #footer>
        <div class="flex w-full justify-end gap-2">
          <UButton
            variant="ghost"
            color="neutral"
            @click="removing = null"
          >
            Cancel
          </UButton>
          <UButton
            color="error"
            icon="i-lucide-trash-2"
            @click="confirmRemove"
          >
            Remove
          </UButton>
        </div>
      </template>
    </UModal>
  </UCard>
</template>
