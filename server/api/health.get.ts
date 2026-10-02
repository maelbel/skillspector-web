export default defineEventHandler(async () => {
  const { apiBase } = useRuntimeConfig()

  return await $fetch<{
    status: string
    mode: 'self_hosted' | 'hosted' | null
    auth: 'none' | 'accounts' | null
    skillspector_version: string
    llm_available: boolean
    claude_cli_available: boolean
    // The deepest a scan may follow a skill's external references; 0 when it can't.
    transitive_max_depth: number
    // How an uploaded file reaches the API (backend/app/uploads.py); null when uploads are off.
    upload_store: 'local' | 'blob' | null
    max_upload_bytes: number
    // What the privacy policy says is kept how long; scan_days is null when scans are kept until
    // deleted, and retention null while the database is unreachable.
    retention: { scan_days: number | null, session_days: number, activity_days: number } | null
  }>('/health', { baseURL: apiBase }).catch(() => ({
    status: 'down',
    mode: null,
    auth: null,
    skillspector_version: 'unknown',
    llm_available: false,
    claude_cli_available: false,
    transitive_max_depth: 0,
    upload_store: null,
    max_upload_bytes: 0,
    retention: null
  }))
})
