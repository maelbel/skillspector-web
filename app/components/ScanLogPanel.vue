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

const CATEGORY_PREFIXES: [RegExp, string][] = [
  [/^static_patterns_/, 'Static pattern: '],
  [/^static_/, 'Static: '],
  [/^semantic_/, 'Semantic: '],
  [/^behavioral_/, 'Behavioral: '],
  [/^mcp_/, 'MCP: ']
]

function humanizeStage(name: string): string {
  let label = name
  for (const [pattern, prefix] of CATEGORY_PREFIXES) {
    if (pattern.test(label)) {
      label = prefix + label.replace(pattern, '')
      break
    }
  }
  label = label.replace(/_/g, ' ')
  return label.charAt(0).toUpperCase() + label.slice(1)
}

interface LogLine {
  icon: string
  class: string
  text: string
}

function parseLine(line: string): LogLine {
  const stageMatch = line.match(/^(.+) completed$/)
  if (stageMatch) {
    return { icon: 'i-lucide-check', class: 'text-gray-400', text: humanizeStage(stageMatch[1]!) }
  }
  if (line.startsWith('Starting scan of')) {
    return { icon: 'i-lucide-play', class: 'text-gray-200 font-medium', text: line }
  }
  if (line === 'Scan complete') {
    return { icon: 'i-lucide-check-circle-2', class: 'text-green-400 font-medium', text: line }
  }
  if (line.startsWith('Scan failed:')) {
    return { icon: 'i-lucide-x-circle', class: 'text-red-400 font-medium', text: line }
  }
  if (line.startsWith('WARNING ')) {
    return { icon: 'i-lucide-alert-triangle', class: 'text-yellow-400', text: line.slice('WARNING '.length) }
  }
  if (line.startsWith('ERROR ')) {
    return { icon: 'i-lucide-alert-circle', class: 'text-red-400', text: line.slice('ERROR '.length) }
  }
  if (line.startsWith('INFO ')) {
    return { icon: 'i-lucide-info', class: 'text-gray-500', text: line.slice('INFO '.length) }
  }
  return { icon: 'i-lucide-minus', class: 'text-gray-500', text: line }
}

const parsedLines = computed(() => props.lines.map(parseLine))
</script>

<template>
  <div
    ref="container"
    class="rounded-md bg-gray-950 font-mono text-xs p-3 max-h-56 overflow-y-auto flex flex-col gap-1"
  >
    <div
      v-for="(line, index) in parsedLines"
      :key="index"
      class="flex items-start gap-1.5"
      :class="line.class"
    >
      <UIcon
        :name="line.icon"
        class="size-3.5 shrink-0 mt-0.5"
      />
      <span class="whitespace-pre-wrap break-all leading-relaxed">{{ line.text }}</span>
    </div>
  </div>
</template>
