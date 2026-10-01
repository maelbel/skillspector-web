export default defineEventHandler(async (event) => {
  await refuseBots(event)
  const { target, upload, ...options } = await readBody<ScanOptionsBody & {
    target?: string
    // A file uploaded to the Blob store first (server/api/scan/upload-token.post.ts).
    upload?: { pathname?: string, name?: string }
  }>(event)

  const blob = upload && typeof upload.pathname === 'string' && typeof upload.name === 'string'
    ? { pathname: upload.pathname, name: upload.name }
    : null
  if (!blob && (!target || typeof target !== 'string')) {
    throw createError({ statusCode: 400, statusMessage: 'Missing "target" in request body' })
  }

  return await backendFetch<{ id: string, status: string }>(event, '/scan', {
    method: 'POST',
    body: { ...(blob ? { upload: blob } : { target }), ...toApiScanOptions(options) },
    fallbackMessage: 'Failed to queue scan'
  })
})
