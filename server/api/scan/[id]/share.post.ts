// A read-only link to the result (the same one if it's already shared).
export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')
  if (!id) {
    throw createError({ statusCode: 400, statusMessage: 'Missing scan id' })
  }
  return await backendFetch<{ token: string }>(event, `/scan/${encodeURIComponent(id)}/share`, {
    method: 'POST',
    fallbackMessage: 'Failed to share the result'
  })
})
