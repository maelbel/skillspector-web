<script setup lang="ts">
// Share a result as a read-only link (backend/app/api/routes/shared.py), or revoke it; and once
// shared, put it on its target's public status badge (backend/app/api/routes/badge.py).
const props = defineProps<{ scanId: string, target: string, privateSource?: boolean }>()
const open = defineModel<boolean>('open', { default: false })
const token = defineModel<string | null>('token', { default: null })
const badge = defineModel<boolean>('badge', { default: false })

type Action = 'create' | 'revoke' | 'badge'
const FAILURES: Record<Action, string> = {
  create: 'Couldn’t create the link',
  revoke: 'Couldn’t revoke the link',
  badge: 'Couldn’t change the badge'
}

// A scan of a private repository (backend/app/repo_connections.py) is shared, or badged, only once
// its owner confirms its result may be public.
const confirmPrivate = ref(false)
const privateBody = () => (props.privateSource ? { confirm_private: confirmPrivate.value } : undefined)

const busy = ref<Action | null>(null)
const errorMessage = ref('')
const copied = ref<'link' | 'badge' | null>(null)
const copyFailed = ref(false)
const linkEl = useTemplateRef<HTMLElement>('linkEl')
const badgeEl = useTemplateRef<HTMLElement>('badgeEl')

const origin = useRequestURL().origin
const link = computed(() => token.value ? `${origin}/shared/${token.value}` : '')
// An upload has no link for a README to name.
const badgeAvailable = computed(() => !!props.target && !isUploadTarget(props.target))
const snippet = computed(() => badgeMarkdown(origin, props.target))
const badgeImage = computed(() => `/badge?target=${encodeURIComponent(props.target)}&v=${badge.value ? 1 : 0}`)

async function run(action: Action, call: () => Promise<void>) {
  busy.value = action
  errorMessage.value = ''
  try {
    await call()
  } catch (err) {
    errorMessage.value = apiErrorMessage(err, FAILURES[action])
  } finally {
    busy.value = null
  }
}

function createLink() {
  copied.value = null
  return run('create', async () => {
    token.value = (await $fetch<{ token: string }>(`/api/scan/${props.scanId}/share`, { method: 'POST', body: privateBody() })).token
  })
}

function revokeLink() {
  return run('revoke', async () => {
    await $fetch(`/api/scan/${props.scanId}/share`, { method: 'DELETE' })
    token.value = null
    // Revoking the link takes the result off the badge too.
    badge.value = false
  })
}

function setBadge(on: boolean) {
  return run('badge', async () => {
    // Turning the switch on is the confirmation: its description says the result becomes public.
    await $fetch(`/api/scan/${props.scanId}/badge`, { method: on ? 'POST' : 'DELETE', body: on && props.privateSource ? { confirm_private: true } : undefined })
    badge.value = on
  })
}

async function copy(what: 'link' | 'badge') {
  try {
    await navigator.clipboard.writeText(what === 'link' ? link.value : snippet.value)
    copied.value = what
    copyFailed.value = false
  } catch {
    // No clipboard access (e.g. plain HTTP): select the text so it can be copied by hand.
    copyFailed.value = true
    const el = what === 'link' ? linkEl.value : badgeEl.value
    if (el) window.getSelection()?.selectAllChildren(el)
  }
}
</script>

<template>
  <UModal
    v-model:open="open"
    title="Share this result"
    description="Anyone with the link can see this result, without signing in. It doesn’t say who scanned it."
  >
    <template #body>
      <div class="flex flex-col gap-4">
        <template v-if="token">
          <div class="flex items-center gap-2 rounded-xs bg-muted p-2 ring ring-default">
            <code
              ref="linkEl"
              class="min-w-0 flex-1 truncate px-1 font-mono text-xs text-highlighted"
            >{{ link }}</code>
            <UButton
              :icon="copied === 'link' ? 'i-lucide-check' : 'i-lucide-copy'"
              color="neutral"
              variant="outline"
              size="sm"
              @click="copy('link')"
            >
              {{ copied === 'link' ? 'Copied' : 'Copy' }}
            </UButton>
          </div>
          <p
            v-if="copyFailed"
            class="text-sm text-muted"
          >
            Couldn’t copy it automatically: it’s selected, so copy it by hand.
          </p>
          <p class="text-sm text-muted">
            Revoking it makes the link stop working at once. Sharing again gives a new one.
          </p>

          <div
            v-if="badgeAvailable"
            class="flex flex-col gap-3 border-t border-default pt-4"
          >
            <USwitch
              :model-value="badge"
              :loading="busy === 'badge'"
              label="Show on the skill’s status badge"
              :description="privateSource
                ? 'This scan read one of your private repositories. A badge shows its verdict and date to anyone, and links to this result.'
                : 'A badge for its README, with the verdict and date of the latest scan of this link put on it. Anyone can see it.'"
              @update:model-value="setBadge"
            />
            <template v-if="badge">
              <img
                :src="badgeImage"
                alt="The status badge"
                class="h-5 self-start"
              >
              <div class="flex items-center gap-2 rounded-xs bg-muted p-2 ring ring-default">
                <code
                  ref="badgeEl"
                  class="min-w-0 flex-1 truncate px-1 font-mono text-xs text-highlighted"
                >{{ snippet }}</code>
                <UButton
                  :icon="copied === 'badge' ? 'i-lucide-check' : 'i-lucide-copy'"
                  color="neutral"
                  variant="outline"
                  size="sm"
                  @click="copy('badge')"
                >
                  {{ copied === 'badge' ? 'Copied' : 'Copy Markdown' }}
                </UButton>
              </div>
              <p class="text-sm text-muted">
                Paste it in the skill’s README. Badges are cached for up to 5 minutes.
              </p>
            </template>
          </div>
        </template>
        <p
          v-else
          class="text-sm text-muted"
        >
          The link shows the verdict, the findings and the files inspected, and lets anyone download
          the report. It works until you revoke it.
        </p>
        <UCheckbox
          v-if="privateSource && !token"
          v-model="confirmPrivate"
          label="Share it anyway"
          description="This scan read one of your private repositories. Anyone with the link will see its findings, with excerpts of its code."
        />

        <UAlert
          v-if="errorMessage"
          color="error"
          variant="subtle"
          :title="errorMessage"
        />
      </div>
    </template>

    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <UButton
          v-if="token"
          color="error"
          variant="ghost"
          :loading="busy === 'revoke'"
          @click="revokeLink"
        >
          Revoke link
        </UButton>
        <UButton
          v-else
          color="primary"
          icon="i-lucide-link"
          :loading="busy === 'create'"
          :disabled="privateSource && !confirmPrivate"
          @click="createLink"
        >
          Create link
        </UButton>
      </div>
    </template>
  </UModal>
</template>
