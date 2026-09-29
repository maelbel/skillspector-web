import type { LLMConfig } from '~~/shared/types/scan'

export default defineEventHandler(async (event) => {
  const { target, llm } = await readBody<{ target?: string, llm?: LLMConfig }>(event)

  if (!target || typeof target !== 'string') {
    throw createError({ statusCode: 400, statusMessage: 'Missing "target" in request body' })
  }

  return await backendFetch<{ id: string, status: string }>(event, '/scan', {
    method: 'POST',
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
    },
    fallbackMessage: 'Failed to queue scan'
  })
})
