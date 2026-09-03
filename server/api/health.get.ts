export default defineEventHandler(async () => {
  const { apiBase } = useRuntimeConfig()

  return await $fetch<{ status: string, skillspector_version: string, llm_available: boolean }>(
    '/health',
    { baseURL: apiBase }
  ).catch(() => ({ status: 'down', skillspector_version: 'unknown', llm_available: false }))
})
