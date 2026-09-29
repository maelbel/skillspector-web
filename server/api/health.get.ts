export default defineEventHandler(async () => {
  const { apiBase } = useRuntimeConfig()

  return await $fetch<{
    status: string
    mode: 'self_hosted' | 'hosted' | null
    skillspector_version: string
    llm_available: boolean
    claude_cli_available: boolean
  }>('/health', { baseURL: apiBase }).catch(() => ({
    status: 'down',
    mode: null,
    skillspector_version: 'unknown',
    llm_available: false,
    claude_cli_available: false
  }))
})
