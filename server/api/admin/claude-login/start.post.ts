export default defineEventHandler(async (event) => {
  const { adminToken } = await readBody<{ adminToken?: string }>(event)

  if (!adminToken) {
    throw createError({ statusCode: 400, statusMessage: 'Missing "adminToken" in request body' })
  }

  const { apiBase } = useRuntimeConfig()

  return await $fetch<{ url: string }>('/admin/claude-login/start', {
    baseURL: apiBase,
    method: 'POST',
    headers: { 'X-Admin-Token': adminToken, 'X-Forwarded-For': getClientIp(event) }
  }).catch((error) => {
    throw createError({
      statusCode: error?.response?.status ?? 502,
      statusMessage: error?.data?.detail ?? 'Failed to start login'
    })
  })
})
