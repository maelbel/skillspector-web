import type { User } from '~~/shared/types/auth'

export default defineEventHandler(async (event) => {
  return await backendFetch<User[]>(event, '/admin/users', { fallbackMessage: 'Failed to load users' })
})
