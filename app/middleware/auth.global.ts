// With accounts on, every page but /login needs a session, and /admin needs the admin role.
export default defineNuxtRouteMiddleware(async (to) => {
  const { session, accounts, user, isAdmin, refresh } = useAuth()
  if (!session.value) await refresh()
  if (!session.value) return // API unreachable: let the page show its own error.

  if (to.path === '/login') {
    if (!accounts.value || user.value) return navigateTo(typeof to.query.redirect === 'string' ? to.query.redirect : '/')
    return
  }
  if (accounts.value && !user.value) {
    return navigateTo({ path: '/login', query: to.fullPath !== '/' ? { redirect: to.fullPath } : {} })
  }
  if (to.path === '/admin' && !isAdmin.value) return navigateTo('/')
})
