export function parseScanTarget(target: string): { title: string, isGithub: boolean } {
  let url: URL
  try {
    url = new URL(target)
  } catch {
    return { title: target, isGithub: false }
  }

  const segments = url.pathname.split('/').filter(Boolean)

  if (url.hostname === 'github.com' && segments.length >= 2) {
    const [owner, repoRaw, kind, ...rest] = segments
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
