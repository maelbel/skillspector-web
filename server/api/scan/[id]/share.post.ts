// A read-only link to the result (the same one if it's already shared).
export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')
  if (!id) {
    throw createError({ statusCode: 400, statusMessage: 'Missing scan id' })
  }
  return await backendFetch<{ token: string }>(event, `/scan/${encodeURIComponent(id)}/share`, {
    method: 'POST',
    // A private repository's scan is only shared, or badged, once its owner confirms.
    body: { confirm_private: await confirmedPrivate(event) },
    fallbackMessage: 'Failed to share the result'
  })
})
