// The GitHub Action's logic that needs neither GitHub nor the server: which skills to scan, whether
// a report fails the check, and what the pull request comment and SARIF upload say.
import { existsSync, readdirSync } from 'node:fs'
import { join, posix } from 'node:path'

export const SKILL_FILE = 'SKILL.md'
// Finds the action's own comment, to update it rather than add another on every push.
export const COMMENT_MARKER = '<!-- skillspector-web-action -->'

const VERDICTS = {
  SAFE: 'Safe to install',
  CAUTION: 'Review before installing',
  DO_NOT_INSTALL: 'Do not install'
}
const VERDICT_ICONS = { SAFE: '🟢', CAUTION: '🟠', DO_NOT_INSTALL: '🔴' }
const FAIL_ON = {
  'do-not-install': ['DO_NOT_INSTALL'],
  'caution': ['CAUTION', 'DO_NOT_INSTALL'],
  'never': []
}

// A folder as a clean posix path relative to the repository: '.' for its root.
function normalize(path) {
  const clean = posix.normalize(path.trim().replaceAll('\\', '/')).replace(/^\.\/+/, '').replace(/\/+$/, '')
  return clean === '' ? '.' : clean
}

/** The `paths` input: folders holding skills, one per line or comma-separated. */
export function parseRoots(input) {
  const roots = String(input ?? '').split(/[\n,]/).map(path => path.trim()).filter(Boolean).map(normalize)
  for (const root of roots) {
    if (root === '..' || root.startsWith('../') || posix.isAbsolute(root)) {
      throw new Error(`"${root}" isn't a folder of the repository: give paths relative to its root`)
    }
  }
  return roots.length ? [...new Set(roots)] : ['.']
}

function within(path, root) {
  return root === '.' || path === root || path.startsWith(`${root}/`)
}

/**
 * The skill a changed file belongs to: the nearest folder holding a SKILL.md, from the file's own
 * folder up to the root it's under. null for a file outside every root or in no skill.
 */
export function skillFor(file, roots, workspace) {
  const path = normalize(file)
  const root = roots.filter(candidate => within(path, candidate)).sort((a, b) => b.length - a.length)[0]
  if (root === undefined) return null
  let folder = posix.dirname(path)
  for (;;) {
    if (existsSync(join(workspace, folder, SKILL_FILE))) return folder
    if (folder === root || folder === '.') return null
    folder = posix.dirname(folder)
  }
}

/** The skills a set of changed files touches, each once, in order. A deleted skill isn't one. */
export function changedSkills(files, roots, workspace) {
  const skills = new Set()
  for (const file of files) {
    const skill = skillFor(file, roots, workspace)
    if (skill !== null) skills.add(skill)
  }
  return [...skills].sort()
}

/** Every skill under the roots: each folder holding a SKILL.md. */
export function allSkills(roots, workspace) {
  const skills = new Set()
  const walk = (folder) => {
    let entries
    try {
      entries = readdirSync(join(workspace, folder), { withFileTypes: true })
    } catch {
      return
    }
    if (entries.some(entry => entry.isFile() && entry.name === SKILL_FILE)) skills.add(folder)
    for (const entry of entries) {
      if (entry.isDirectory() && entry.name !== '.git' && entry.name !== 'node_modules') {
        walk(folder === '.' ? entry.name : `${folder}/${entry.name}`)
      }
    }
  }
  roots.forEach(walk)
  return [...skills].sort()
}

/** The threshold inputs, checked: `fail-on` and `max-risk-score`. */
export function parseThreshold(failOn, maxRiskScore) {
  const level = String(failOn || 'do-not-install').trim().toLowerCase()
  if (!(level in FAIL_ON)) {
    throw new Error(`fail-on is "${failOn}": use do-not-install, caution or never`)
  }
  const raw = String(maxRiskScore ?? '').trim()
  const score = raw === '' ? null : Number(raw)
  if (score !== null && !(Number.isInteger(score) && score >= 0 && score <= 100)) {
    throw new Error(`max-risk-score is "${maxRiskScore}": give a whole number from 0 to 100`)
  }
  return { failOn: level, maxRiskScore: score }
}

/**
 * A finished scan's risk assessment: the report's own, or for a folder that held several skills,
 * the riskiest of theirs.
 */
export function riskOf(result) {
  if (result?.risk_assessment) return result.risk_assessment
  const assessments = (result?.skills ?? []).map(skill => skill.risk_assessment ?? skill.report?.risk_assessment).filter(Boolean)
  return assessments.sort((a, b) => (b.score ?? 0) - (a.score ?? 0))[0] ?? null
}

export function issueCount(result) {
  if (Array.isArray(result?.issues)) return result.issues.length
  return (result?.skills ?? []).reduce((count, skill) => count + (skill.issue_count ?? skill.report?.issues?.length ?? 0), 0)
}

/** Why a scanned skill fails the check, or null when it passes. A scan that failed always does. */
export function failureReason(outcome, threshold) {
  if (outcome.error) return 'it couldn’t be scanned'
  const risk = outcome.risk
  if (!risk) return 'its report has no risk assessment'
  if (FAIL_ON[threshold.failOn].includes(risk.recommendation)) return `its verdict is “${VERDICTS[risk.recommendation]}”`
  if (threshold.maxRiskScore !== null && risk.score > threshold.maxRiskScore) {
    return `its risk score, ${risk.score}, is above ${threshold.maxRiskScore}`
  }
  return null
}

function isRelative(uri) {
  return typeof uri === 'string' && uri !== '' && !/^[a-z][a-z0-9+.-]*:/i.test(uri) && !uri.startsWith('/')
}

/**
 * One skill's SARIF, as a code scanning upload wants it: its files' paths from the repository's
 * root rather than the skill's folder, and a category of its own, so each skill's alerts are kept
 * until that skill is scanned again rather than replaced by another skill's.
 */
export function repositorySarif(log, skill) {
  const prefix = skill === '.' ? '' : `${skill}/`
  const fix = (value) => {
    if (Array.isArray(value)) return value.map(fix)
    if (value === null || typeof value !== 'object') return value
    const copy = {}
    for (const [key, inner] of Object.entries(value)) {
      copy[key] = (key === 'artifactLocation' || key === 'location') && isRelative(inner?.uri)
        ? { ...fix(inner), uri: prefix + inner.uri }
        : fix(inner)
    }
    return copy
  }
  return {
    ...log,
    runs: (log.runs ?? []).map(run => ({ ...fix(run), automationDetails: { id: `skillspector/${skill === '.' ? 'root' : skill}/` } }))
  }
}

/** Every skill's SARIF as one log, with a run per skill. */
export function mergeSarif(logs) {
  if (!logs.length) return null
  return { ...logs[0], runs: logs.flatMap(log => log.runs ?? []) }
}

function cell(text) {
  return String(text).replaceAll('|', '\\|').replaceAll('\n', ' ')
}

/** The pull request comment and job summary: a row per skill, with a link to its report. */
export function renderSummary(outcomes, { threshold }) {
  const failed = outcomes.filter(outcome => outcome.failure)
  const lines = [COMMENT_MARKER, '## Skillspector scan', '']
  if (!outcomes.length) {
    lines.push('This pull request changes no skill, so nothing was scanned.')
    return lines.join('\n')
  }
  lines.push(failed.length
    ? `❌ ${failed.length} of ${outcomes.length} skill${outcomes.length === 1 ? '' : 's'} failed the check.`
    : `✅ ${outcomes.length === 1 ? 'The skill' : `All ${outcomes.length} skills`} passed the check.`)
  lines.push('', '| Skill | Verdict | Risk score | Findings | Report |', '|---|---|---|---|---|')
  for (const outcome of outcomes) {
    const risk = outcome.risk
    const verdict = outcome.error
      ? '⚠️ Not scanned'
      : risk ? `${VERDICT_ICONS[risk.recommendation] ?? ''} ${VERDICTS[risk.recommendation] ?? risk.recommendation}`.trim() : '—'
    const report = outcome.reportUrl ? `[View report](${outcome.reportUrl})` : '—'
    lines.push(`| \`${cell(outcome.skill)}\` | ${verdict} | ${risk ? `${risk.score}/100` : '—'} | ${outcome.error ? '—' : outcome.issues ?? 0} | ${report} |`)
  }
  const notes = outcomes.filter(outcome => outcome.failure || outcome.error)
  if (notes.length) {
    lines.push('')
    for (const outcome of notes) {
      lines.push(`- \`${cell(outcome.skill)}\` fails: ${outcome.failure}${outcome.error ? ` (${cell(outcome.error)})` : ''}.`)
    }
  }
  const rules = [
    threshold.failOn === 'never' ? null : `fails on “${threshold.failOn === 'caution' ? VERDICTS.CAUTION : VERDICTS.DO_NOT_INSTALL}”${threshold.failOn === 'caution' ? ' or worse' : ''}`,
    threshold.maxRiskScore === null ? null : `fails on a risk score above ${threshold.maxRiskScore}`
  ].filter(Boolean)
  lines.push('', `<sub>${rules.length ? `The check ${rules.join(' and ')}.` : 'The check doesn’t fail on a verdict.'} Reports open for the API token’s owner and admins.</sub>`)
  return lines.join('\n')
}
