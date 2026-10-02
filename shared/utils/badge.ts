import type { Recommendation } from '../types/scan'

// A target's status badge (server/routes/badge.get.ts): the verdict of the latest scan its owner
// put on it, in the flat style READMEs already use for CI and coverage badges.

export interface BadgeData {
  recommendation: Recommendation | null
  risk_score: number | null
  scanned_at: number | null
  share_token: string | null
}

const BADGE_LABEL = 'skillspector'

const VERDICTS: Record<Recommendation, { text: string, color: string }> = {
  SAFE: { text: 'safe', color: '#1a7f37' },
  CAUTION: { text: 'review first', color: '#9a6700' },
  DO_NOT_INSTALL: { text: 'do not install', color: '#cf222e' }
}
const UNKNOWN = { text: 'unknown', color: '#6e7781' }

// Verdana at 11px, which the badge is drawn in, near enough to size each half to its text.
function textWidth(text: string): number {
  let width = 0
  for (const char of text) {
    if ('ijlt.,:;|!\'’ '.includes(char)) width += 3.9
    else if ('frI()[]-·'.includes(char)) width += 4.7
    else if ('mwMW'.includes(char)) width += 10.5
    else if (/[A-Z]/.test(char)) width += 7.6
    else width += 6.8
  }
  return Math.ceil(width)
}

function escapeXml(text: string): string {
  return text.replace(/[<>&"']/g, char => `&#${char.charCodeAt(0)};`)
}

/** What the badge says: the verdict and the scan's date, or "unknown" without a scan on it. */
export function badgeMessage(data: Partial<BadgeData>): { text: string, color: string } {
  const verdict = data.recommendation ? VERDICTS[data.recommendation] : undefined
  if (!verdict) return UNKNOWN
  const date = data.scanned_at ? ` · ${new Date(data.scanned_at * 1000).toISOString().slice(0, 10)}` : ''
  return { text: `${verdict.text}${date}`, color: verdict.color }
}

export function renderBadge(data: Partial<BadgeData>): string {
  const message = badgeMessage(data)
  const labelWidth = textWidth(BADGE_LABEL) + 12
  const messageWidth = textWidth(message.text) + 12
  const width = labelWidth + messageWidth
  const title = escapeXml(`${BADGE_LABEL}: ${message.text}`)
  const half = (text: string, x: number) => `<text x="${x}" y="15" fill="#010101" fill-opacity=".3">${escapeXml(text)}</text>`
    + `<text x="${x}" y="14">${escapeXml(text)}</text>`
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="20" role="img" aria-label="${title}">`
    + `<title>${title}</title>`
    + '<linearGradient id="s" x2="0" y2="100%"><stop offset="0" stop-color="#bbb" stop-opacity=".1"/><stop offset="1" stop-opacity=".1"/></linearGradient>'
    + `<clipPath id="r"><rect width="${width}" height="20" rx="3" fill="#fff"/></clipPath>`
    + `<g clip-path="url(#r)"><rect width="${labelWidth}" height="20" fill="#555"/><rect x="${labelWidth}" width="${messageWidth}" height="20" fill="${message.color}"/><rect width="${width}" height="20" fill="url(#s)"/></g>`
    + '<g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="11">'
    + half(BADGE_LABEL, labelWidth / 2) + half(message.text, labelWidth + messageWidth / 2)
    + '</g></svg>'
}

/** The Markdown a README shows the badge with, linking to the result it shows. */
export function badgeMarkdown(origin: string, target: string): string {
  const query = `target=${encodeURIComponent(target)}`
  return `[![Skillspector verdict](${origin}/badge?${query})](${origin}/badge/report?${query})`
}
