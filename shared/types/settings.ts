export interface SettingsResponse {
  scan_retention_days: number | null
  // Whether visitors may create their own account; always false without accounts.
  allow_signup: boolean
  // Whether new scans are refused, for everyone.
  scans_paused: boolean
  // Per signed-in user other than admins; null means no limit.
  daily_scan_quota: number | null
  concurrent_scan_quota: number | null
}

export interface UsageResponse {
  scans_paused: boolean
  // False for admins, and without accounts: no quota applies to them.
  quotas_apply: boolean
  // Scans started in the last 24 hours, including deleted ones.
  scans_today: number
  daily_scan_quota: number | null
  active_scans: number
  concurrent_scan_quota: number | null
}
