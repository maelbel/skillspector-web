export default defineEventHandler(async (event) => {
  const { adminToken, code } = await readBody<{ adminToken?: string, code?: string }>(event)

  if (!adminToken) {
    throw createError({ statusCode: 400, statusMessage: 'Missing "adminToken" in request body' })
  }
  if (!code) {
    throw createError({ statusCode: 400, statusMessage: 'Missing "code" in request body' })
  }

  const { apiBase } = useRuntimeConfig()

  return await $fetch<{ success: boolean, output: string }>('/admin/claude-login/complete', {
    baseURL: apiBase,
    method: 'POST',
    headers: { 'X-Admin-Token': adminToken },
    body: { code }
  }).catch((error) => {
    throw createError({
      statusCode: error?.response?.status ?? 502,
      statusMessage: error?.data?.detail ?? 'Failed to complete login'
    })
  })
})
