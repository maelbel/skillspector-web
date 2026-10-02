// Where the caller's Blob uploads go (upload-token.post.ts only allows that folder): a script with
// an API token, the GitHub Action (action/), names its upload's pathname after it.
export default defineEventHandler(async (event) => {
  return await backendFetch<{ folder: string }>(event, '/scan/upload-folder', {
    fallbackMessage: 'Failed to check your session'
  })
})
