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
  quotas: UserQuotas
}

// A user's scan quotas (backend/app/quotas.py): their own (null follows the server's, 0 is no
// limit), the server's as it applies now (null: no limit), and today's use.
export interface UserQuotas {
  daily_scan_quota: number | null
  concurrent_scan_quota: number | null
  server_daily_scan_quota: number | null
  server_concurrent_scan_quota: number | null
  // False for an admin: quotas don't apply to them.
  applies: boolean
  scans_today: number
  active_scans: number
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

// The monitoring page (backend/app/api/routes/backoffice.py).
export interface AlertRule {
  name: string
  title: string
  condition: string
  cooldown_minutes: number
  // False for a hosted-only rule on a self-hosted server.
  applies: boolean
  tripped: boolean
  current: string | null
  last_alert_at: number | null
  // Set while the rule waits out its cooldown after an alert.
  quiet_until: number | null
}

export interface Monitoring {
  health: Health
  rules: AlertRule[]
  // The webhook by its host only: its path is its secret.
  channels: { webhook_host: string | null, emails: string[], email_ready: boolean }
}

export type MonitorEventKind = 'scan_failed' | 'sandbox_error' | 'queue_redelivered' | 'bot_refused' | 'alert_sent'
export type MonitorEventFilter = 'all' | 'failures' | 'sandbox' | 'redeliveries' | 'bots' | 'alerts'

export interface MonitorEvent {
  id: number
  created_at: number
  kind: MonitorEventKind
  message: string | null
  scan_id: string | null
  count: number
}

export interface MonitorEventPage {
  items: MonitorEvent[]
  total: number
}
