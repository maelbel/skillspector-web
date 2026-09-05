export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')
  if (!id) {
    throw createError({ statusCode: 400, statusMessage: 'Missing scan id' })
  }

  const { adminToken } = await readBody<{ adminToken?: string }>(event)
  if (!adminToken) {
    throw createError({ statusCode: 400, statusMessage: 'Missing "adminToken" in request body' })
  }

  const { apiBase } = useRuntimeConfig()

  await $fetch(`/scan/${id}`, {
    baseURL: apiBase,
    method: 'DELETE',
    headers: { 'X-Admin-Token': adminToken }
  }).catch((error) => {
    throw createError({
      statusCode: error?.response?.status ?? 502,
      statusMessage: error?.data?.detail ?? 'Failed to delete scan'
    })
  })

  return { success: true }
})
