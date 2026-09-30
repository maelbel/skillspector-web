export type AuthMode = 'none' | 'accounts'

export type UserRole = 'admin' | 'user'

export type UserStatus = 'active' | 'suspended'

export interface User {
  id: string
  email: string
  role: UserRole
  status: UserStatus
  created_at: number
  last_login_at: number | null
}

export interface AuthSession {
  auth: AuthMode
  user: User | null
  needs_setup: boolean
  signup_allowed: boolean
  // "Forgot password?" by email is available.
  email_enabled: boolean
}
