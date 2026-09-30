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
}

export interface Overview {
  auth: 'none' | 'accounts'
  email_enabled: boolean
  signup_allowed: boolean
  // "new" and "recent" count the last 7 days.
  users: { total: number, admins: number, suspended: number, new: number }
  scans: { total: number, recent: number, do_not_install: number, caution: number, safe: number, failed: number, active: number }
  recent_activity: ActivityEntry[]
}

export interface ActivityPage {
  items: ActivityEntry[]
  total: number
}
