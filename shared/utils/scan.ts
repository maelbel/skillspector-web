export function parseScanTarget(target: string): { title: string, isGithub: boolean } {
  let url: URL
  try {
    url = new URL(target)
  } catch {
    return { title: target, isGithub: false }
  }

  const segments = url.pathname.split('/').filter(Boolean)

  if (url.hostname === 'github.com' && segments.length >= 2) {
    const [owner, repoRaw = '', kind, ...rest] = segments
    const repo = repoRaw.replace(/\.git$/i, '')
    const path = (kind === 'tree' || kind === 'blob') && rest.length > 1 ? rest.slice(1).join('/') : ''
    return { title: path ? `${owner}/${repo}/${path}` : `${owner}/${repo}`, isGithub: true }
  }

  if (url.hostname === 'raw.githubusercontent.com' && segments.length >= 3) {
    const [owner, repo, , ...rest] = segments
    const path = rest.join('/')
    return { title: path ? `${owner}/${repo}/${path}` : `${owner}/${repo}`, isGithub: true }
  }

  return { title: target, isGithub: false }
}

export type ScanTargetKind = 'repository' | 'file' | 'archive'

export type ScanTargetInfo
  = | { ok: true, kind: ScanTargetKind, host: string, title: string }
    | { ok: false, problem: string }

// Mirrors skillspector's input_handler: only these hosts are fetched, only over https, and on
// Git hosts anything that isn't a /blob/, /raw/ or /archive/ link (or a .md/.py/.sh file) is
// `git clone`d as-is — which is why folder (/tree/) links fail.
const GIT_HOSTS: Record<string, string> = {
  'github.com': 'GitHub',
  'gitlab.com': 'GitLab',
  'bitbucket.org': 'Bitbucket'
}
const DOWNLOAD_HOSTS: Record<string, string> = {
  'raw.githubusercontent.com': 'GitHub',
  'huggingface.co': 'Hugging Face'
}
const DIRECT_FILE_SUFFIXES = ['.md', '.py', '.sh']
const SUPPORTED_HOSTS = 'GitHub, GitLab, Bitbucket or Hugging Face'

export function describeScanTarget(target: string): ScanTargetInfo | null {
  const value = target.trim()
  if (!value) return null

  let url: URL
  try {
    url = new URL(value)
  } catch {
    return { ok: false, problem: 'Enter a full URL, starting with https://' }
  }
  if (url.protocol !== 'https:') {
    return { ok: false, problem: 'Only https:// URLs can be scanned' }
  }

  const hostName = GIT_HOSTS[url.hostname] ?? DOWNLOAD_HOSTS[url.hostname]
  if (!hostName) {
    return { ok: false, problem: `Only ${SUPPORTED_HOSTS} URLs can be scanned` }
  }

  const path = url.pathname.toLowerCase()
  const { title } = parseScanTarget(value)
  const kind: ScanTargetKind = path.endsWith('.zip') || path.includes('/archive/')
    ? 'archive'
    : 'file'

  if (url.hostname in DOWNLOAD_HOSTS) {
    return { ok: true, kind, host: hostName, title }
  }
  if (path.includes('/tree/')) {
    return { ok: false, problem: 'Folder links can’t be scanned — link the repository itself, or a SKILL.md file inside it' }
  }
  if (['/blob/', '/raw/', '/archive/'].some(part => path.includes(part)) || DIRECT_FILE_SUFFIXES.some(suffix => path.endsWith(suffix))) {
    return { ok: true, kind, host: hostName, title }
  }
  if (url.pathname.split('/').filter(Boolean).length < 2) {
    return { ok: false, problem: `Link to a repository, e.g. https://${url.hostname}/org/repo` }
  }
  return { ok: true, kind: 'repository', host: hostName, title }
}
