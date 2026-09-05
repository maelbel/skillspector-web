import type { LLMConfig } from '~~/shared/types/scan'

export default defineEventHandler(async (event) => {
  const { target, llm } = await readBody<{ target?: string, llm?: LLMConfig }>(event)

  if (!target || typeof target !== 'string') {
    throw createError({ statusCode: 400, statusMessage: 'Missing "target" in request body' })
  }

  const { apiBase } = useRuntimeConfig()
  const clientIp = getRequestIP(event, { xForwardedFor: true }) ?? 'unknown'

  return await $fetch<{ id: string, status: string }>('/scan', {
    baseURL: apiBase,
    method: 'POST',
    headers: { 'X-Forwarded-For': clientIp },
    body: {
      target,
      llm: llm
        ? {
            provider: llm.provider,
            api_key: llm.apiKey,
            base_url: llm.baseUrl,
            model: llm.model
          }
        : null
    }
  }).catch((error) => {
    throw createError({
      statusCode: error?.response?.status ?? 502,
      statusMessage: error?.data?.detail?.[0]?.msg ?? error?.data?.detail ?? 'Failed to queue scan'
    })
  })
})
