import { handleUpload, type HandleUploadBody } from '@vercel/blob/client'

// Hosted uploads: function request bodies are limited to 4.5 MB, so the browser uploads straight
// to the project's private Blob store, with a token from here (@vercel/blob's client upload). The
// token only allows a .zip or .md, no larger than the API takes, under uploads/<the user's id>/:
// the API then scans it by that pathname, checking it's the user's own (backend/app/uploads.py).
// A script uploads the same way, with its API token (the GitHub Action, action/).
export default defineEventHandler(async (event) => {
  await refuseBots(event)
  const body = await readBody<HandleUploadBody>(event)
  // The API names the folder, for a session or an API token, and answers 401 for neither.
  const { folder } = await backendFetch<{ folder: string }>(event, '/scan/upload-folder', { fallbackMessage: 'Failed to check your session' })
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
