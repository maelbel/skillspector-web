import type { AIUsage } from './settings'
import type { Recommendation } from './scan'
import type { User } from './auth'

export interface DirectoryUser extends User {
  scan_count: number
}

export interface ActivityEntry {
  id: number
  created_at: number
  actor_id: string | null
  actor_email: string | null
  action: string
  target_id: string | null
  target_email: string | null
  detail: string | null
}

export interface UserDetail {
  user: DirectoryUser
  recent_scans: {
    id: string
    target: string
    status: string
    created_at: number
    recommendation: Recommendation | null
    risk_score: number | null
  }[]
  activity: ActivityEntry[]
  ai_usage: AIUsage
}

export interface Overview {
  auth: 'none' | 'accounts'
  email_enabled: boolean
  signup_allowed: boolean
  // "new" and "recent" count the last 7 days.
  users: { total: number, admins: number, suspended: number, new: number }
  scans: { total: number, recent: number, do_not_install: number, caution: number, safe: number, failed: number, active: number }
  recent_activity: ActivityEntry[]
  health: Health
}

// What went wrong over the last `hours` (backend/app/monitoring.py).
export interface Health {
  hours: number
  finished: number
  failed: number
  sandbox_errors: number
  redeliveries: number
  bot_refusals: number
  last_error: { kind: 'scan_failed' | 'sandbox_error', message: string | null, at: number, scan_id: string | null } | null
  // Where alerts go; empty when they aren't set up.
  alert_channels: ('webhook' | 'email')[]
  last_alert: { rule: string | null, at: number } | null
}

export interface ActivityPage {
  items: ActivityEntry[]
  total: number
}
