<script setup lang="ts">
// Share a result as a read-only link (backend/app/api/routes/shared.py), or revoke it.
const props = defineProps<{ scanId: string }>()
const open = defineModel<boolean>('open', { default: false })
const token = defineModel<string | null>('token', { default: null })

const busy = ref<'create' | 'revoke' | null>(null)
const errorMessage = ref('')
const copied = ref(false)
const copyFailed = ref(false)
const linkEl = useTemplateRef<HTMLElement>('linkEl')

const origin = useRequestURL().origin
const link = computed(() => token.value ? `${origin}/shared/${token.value}` : '')

async function run(action: 'create' | 'revoke', call: () => Promise<void>) {
  busy.value = action
  errorMessage.value = ''
  try {
    await call()
  } catch (err) {
    errorMessage.value = apiErrorMessage(err, action === 'create' ? 'Couldn’t create the link' : 'Couldn’t revoke the link')
  } finally {
    busy.value = null
  }
}

function createLink() {
  copied.value = false
  return run('create', async () => {
    token.value = (await $fetch<{ token: string }>(`/api/scan/${props.scanId}/share`, { method: 'POST' })).token
  })
}

function revokeLink() {
  return run('revoke', async () => {
    await $fetch(`/api/scan/${props.scanId}/share`, { method: 'DELETE' })
    token.value = null
  })
}

async function copyLink() {
  try {
    await navigator.clipboard.writeText(link.value)
    copied.value = true
    copyFailed.value = false
  } catch {
    // No clipboard access (e.g. plain HTTP): select the link so it can be copied by hand.
    copyFailed.value = true
    if (linkEl.value) window.getSelection()?.selectAllChildren(linkEl.value)
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
              :icon="copied ? 'i-lucide-check' : 'i-lucide-copy'"
              color="neutral"
              variant="outline"
              size="sm"
              @click="copyLink"
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
          <p class="text-sm text-muted">
            Revoking it makes the link stop working at once. Sharing again gives a new one.
          </p>
        </template>
        <p
          v-else
          class="text-sm text-muted"
        >
          The link shows the verdict, the findings and the files inspected, and lets anyone download
          the report. It works until you revoke it.
        </p>

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
          @click="createLink"
        >
          Create link
        </UButton>
      </div>
    </template>
  </UModal>
</template>
