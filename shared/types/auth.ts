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
  // Users can save their own Claude key, and the signed-in user's saved key, if any.
  claude_key_available: boolean
  claude_key: ClaudeKeyStatus | null
}

export interface ClaudeKeyStatus {
  provider: 'anthropic'
  // The last characters of the key, e.g. "…a1b2"; the key itself never comes back.
  hint: string
  updated_at: number
}
