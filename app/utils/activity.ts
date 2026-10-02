import type { ActivityEntry } from '~~/shared/types/backoffice'

// How each audit action reads in the activity log: "<actor> <verb> <target>".
const VERBS: Record<string, { verb: string, icon: string }> = {
  'account.created': { verb: 'created the account of', icon: 'i-lucide-user-plus' },
  'user.role_changed': { verb: 'changed the role of', icon: 'i-lucide-shield-half' },
  'user.suspended': { verb: 'suspended', icon: 'i-lucide-user-x' },
  'user.quotas_changed': { verb: 'changed the scan quotas of', icon: 'i-lucide-gauge' },
  'user.reactivated': { verb: 'reactivated', icon: 'i-lucide-user-check' },
  'user.deleted': { verb: 'deleted', icon: 'i-lucide-trash-2' },
  'password.reset_link_created': { verb: 'created a password reset link for', icon: 'i-lucide-link' },
  'password.reset_email_sent': { verb: 'emailed a password reset link to', icon: 'i-lucide-mail' },
  'password.reset': { verb: 'reset the password of', icon: 'i-lucide-key-round' },
  'password.changed': { verb: 'changed the password of', icon: 'i-lucide-key-round' },
  'account.claude_connected': { verb: 'connected a Claude key for', icon: 'i-lucide-plug' },
  'account.claude_disconnected': { verb: 'disconnected the Claude key of', icon: 'i-lucide-unplug' },
  'settings.retention_changed': { verb: 'changed scan retention', icon: 'i-lucide-archive' },
  'settings.signup_changed': { verb: 'turned sign-up', icon: 'i-lucide-door-open' },
  'settings.scans_paused': { verb: 'paused new scans', icon: 'i-lucide-circle-pause' },
  'settings.scans_resumed': { verb: 'resumed scans', icon: 'i-lucide-circle-play' },
  'settings.quotas_changed': { verb: 'changed scan quotas', icon: 'i-lucide-gauge' },
  'scan.shared': { verb: 'shared the result of a scan of', icon: 'i-lucide-link' },
  'scan.unshared': { verb: 'revoked the shared link to a scan of', icon: 'i-lucide-unlink' },
  'scan.badge_added': { verb: 'added to a status badge a scan of', icon: 'i-lucide-badge-check' },
  'scan.badge_removed': { verb: 'removed from a status badge a scan of', icon: 'i-lucide-badge-x' },
  'token.created': { verb: 'created an API token for', icon: 'i-lucide-key-square' },
  'token.used': { verb: 'used an API token of', icon: 'i-lucide-terminal' },
  'token.revoked': { verb: 'revoked an API token of', icon: 'i-lucide-key-square' }
}

export interface ActivityLine {
  icon: string
  actor: string
  verb: string
  // Omitted when the actor acted on their own account ("signed up", "changed their password").
  target: string | null
  detail: string | null
}

export function describeActivity(entry: ActivityEntry): ActivityLine {
  const known = VERBS[entry.action] ?? { verb: entry.action, icon: 'i-lucide-dot' }
  const actor = entry.actor_email ?? 'Someone'
  const self = entry.actor_id !== null && entry.actor_id === entry.target_id
  if (self && entry.action === 'account.created') {
    return { icon: known.icon, actor, verb: entry.detail === 'signed up' ? 'signed up' : 'created the first admin account', target: null, detail: null }
  }
  if (self && entry.action === 'password.reset_email_sent') {
    return { icon: known.icon, actor, verb: 'asked for a password reset email', target: null, detail: null }
  }
  if (self && entry.action === 'account.claude_connected') {
    return { icon: known.icon, actor, verb: 'connected their Claude key', target: null, detail: entry.detail }
  }
  if (self && entry.action === 'account.claude_disconnected') {
    return { icon: known.icon, actor, verb: 'disconnected their Claude key', target: null, detail: null }
  }
  if (self && entry.action.startsWith('password.')) {
    return { icon: known.icon, actor, verb: known.verb.replace(/ (of|for|to)$/, '').replace('the password', 'their password'), target: null, detail: entry.detail }
  }
  if (self && entry.action.startsWith('token.')) {
    const verb = { 'token.created': 'created an API token', 'token.used': 'used an API token', 'token.revoked': 'revoked an API token' }[entry.action]
    return { icon: known.icon, actor, verb: verb ?? known.verb, target: null, detail: entry.detail }
  }
  if (entry.action === 'settings.signup_changed') {
    return { icon: known.icon, actor, verb: `${known.verb} ${entry.detail ?? ''}`.trim(), target: null, detail: null }
  }
  return { icon: known.icon, actor, verb: known.verb, target: entry.target_email, detail: entry.detail }
}
