export default defineEventHandler(async (event) => {
  const { currentPassword, newPassword } = await readBody<{ currentPassword?: string, newPassword?: string }>(event)

  await backendFetch(event, '/auth/password', {
    method: 'POST',
    body: { current_password: currentPassword, new_password: newPassword },
    fallbackMessage: 'Failed to change the password'
  })
  return { success: true }
})
