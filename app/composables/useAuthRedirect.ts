// Where to go after signing in: the page that sent the visitor to sign in, if it's one of ours.
export function useAuthRedirect() {
  const route = useRoute()
  return computed(() => {
    const target = route.query.redirect
    return typeof target === 'string' && target.startsWith('/') && !target.startsWith('//') ? target : '/'
  })
}
