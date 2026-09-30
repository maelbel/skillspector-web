// Vercel Cron's retention sweep on the hosted version (scheduled in vercel.ts). Cron sends
// CRON_SECRET as a bearer token, passed on as is: the API checks it.
export default defineEventHandler(async (event) => {
  const authorization = getHeader(event, 'authorization')

  return await backendFetch<{ deleted: number }>(event, '/internal/retention', {
    method: 'POST',
    headers: authorization ? { Authorization: authorization } : {},
    fallbackMessage: 'Retention sweep failed'
  })
})
