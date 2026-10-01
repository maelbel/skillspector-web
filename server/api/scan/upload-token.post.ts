import { handleUpload, type HandleUploadBody } from '@vercel/blob/client'
import type { AuthSession } from '~~/shared/types/auth'

// Hosted uploads: function request bodies are limited to 4.5 MB, so the browser uploads straight
// to the project's private Blob store, with a token from here (@vercel/blob's client upload). The
// token only allows a .zip or .md, no larger than the API takes, under uploads/<the user's id>/:
// the API then scans it by that pathname, checking it's the user's own (backend/app/uploads.py).
export default defineEventHandler(async (event) => {
  await refuseBots(event)
  const body = await readBody<HandleUploadBody>(event)
  const session = await backendFetch<AuthSession>(event, '/auth/session', { fallbackMessage: 'Failed to check your session' })
  if (session.auth === 'accounts' && !session.user) {
    throw createError({ statusCode: 401, statusMessage: 'Sign in to continue' })
  }
  const folder = `uploads/${session.user?.id ?? 'anonymous'}/`
  const { max_upload_bytes: maxBytes } = await $fetch<{ max_upload_bytes: number }>('/api/health')

  try {
    return await handleUpload({
      body,
      request: toWebRequest(event),
      onBeforeGenerateToken: async (pathname) => {
        const name = pathname.slice(folder.length)
        if (!pathname.startsWith(folder) || !name || name.includes('/') || !/\.(zip|md)$/i.test(name)) {
          throw new Error('Upload a .zip of the skill, or its SKILL.md')
        }
        return {
          allowedContentTypes: ['application/zip', 'application/x-zip-compressed', 'text/markdown', 'text/plain', 'application/octet-stream'],
          maximumSizeInBytes: maxBytes,
          addRandomSuffix: true
        }
      }
    })
  } catch (error) {
    throw createError({ statusCode: 400, statusMessage: error instanceof Error ? error.message : 'Couldn’t start the upload' })
  }
})
