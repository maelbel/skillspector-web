export type AuthMode = 'none' | 'accounts'

export type UserRole = 'admin' | 'user'

export interface User {
  id: string
  email: string
  role: UserRole
  created_at: number
}

export interface AuthSession {
  auth: AuthMode
  user: User | null
  needs_setup: boolean
  signup_allowed: boolean
}
