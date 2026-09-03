export default defineEventHandler(async (event) => {
  const { target, useLlm } = await readBody<{ target?: string, useLlm?: boolean }>(event)

  if (!target || typeof target !== 'string') {
    throw createError({ statusCode: 400, statusMessage: 'Missing "target" in request body' })
  }

  const { apiBase } = useRuntimeConfig()

  return await $fetch<{ id: string, status: string }>('/scan', {
    baseURL: apiBase,
    method: 'POST',
    body: { target, use_llm: Boolean(useLlm) }
  }).catch((error) => {
    throw createError({
      statusCode: error?.response?.status ?? 502,
      statusMessage: error?.data?.detail?.[0]?.msg ?? error?.data?.detail ?? 'Failed to queue scan'
    })
  })
})
