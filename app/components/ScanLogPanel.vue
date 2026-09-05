<script setup lang="ts">
const props = defineProps<{
  lines: string[]
}>()

const container = ref<HTMLElement>()

watch(() => props.lines.length, () => {
  nextTick(() => {
    const el = container.value
    if (el) el.scrollTop = el.scrollHeight
  })
})
</script>

<template>
  <div
    ref="container"
    class="rounded-md bg-gray-950 text-gray-200 font-mono text-xs p-3 max-h-56 overflow-y-auto"
  >
    <p
      v-for="(line, index) in lines"
      :key="index"
      class="whitespace-pre-wrap break-all leading-relaxed"
    >
      {{ line }}
    </p>
  </div>
</template>
