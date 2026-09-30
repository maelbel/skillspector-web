export interface SettingsResponse {
  scan_retention_days: number | null
  // Whether visitors may create their own account; always false without accounts.
  allow_signup: boolean
}
