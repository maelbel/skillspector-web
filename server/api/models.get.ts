// The models skillspector knows per provider, for the scan form's model picker.
export default defineEventHandler(async (event) => {
  return await backendFetch<Record<string, { default: string | null, models: string[] }>>(event, '/models', {
    fallbackMessage: 'Failed to fetch the model list'
  })
})
