// The GitHub Action (../action.yml): scans the skills a pull request or push changes on a
// Skillspector Web server, comments on the pull request, and writes the findings as SARIF. Node's
// own modules only, so the action installs nothing, except @vercel/blob for a hosted server.
import { execFileSync } from 'node:child_process'
import { appendFileSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { join } from 'node:path'
import { pathToFileURL } from 'node:url'
import {
  COMMENT_MARKER, allSkills, changedSkills, failureReason, issueCount, mergeSarif, parseRoots,
  parseThreshold, renderSummary, repositorySarif, riskOf
} from './lib.mjs'
import { zipDirectory } from './zip.mjs'

// The @vercel/blob the web app uses (package.json), for its client upload protocol.
const BLOB_PACKAGE = '@vercel/blob@2.8.0'
const POLL_SECONDS = 5
// GitHub's lists of a pull request's or a comparison's files stop here: past it, scan every skill.
const PULL_FILES_LIMIT = 3000
const COMPARE_FILES_LIMIT = 300

const env = process.env

function input(name, fallback = '') {
  const value = env[`INPUT_${name.toUpperCase().replaceAll('-', '_')}`]
  return value === undefined || value.trim() === '' ? fallback : value.trim()
}

function setOutput(name, value) {
  if (env.GITHUB_OUTPUT) appendFileSync(env.GITHUB_OUTPUT, `${name}<<__skillspector__\n${value}\n__skillspector__\n`)
}

const sleep = seconds => new Promise(resolve => setTimeout(resolve, seconds * 1000))

function message(body, fallback) {
  // FastAPI's `detail`, or a Nitro error's `message`.
  const detail = body?.detail ?? body?.message ?? body?.statusMessage
  if (typeof detail === 'string' && detail) return detail
  if (Array.isArray(detail) && typeof detail[0]?.msg === 'string') return detail[0].msg
  return fallback
}

class Skillspector {
  constructor(serverUrl, token) {
    this.server = serverUrl.replace(/\/+$/, '')
    this.token = token
  }

  get headers() {
    return this.token ? { Authorization: `Bearer ${this.token}` } : {}
  }

  async request(path, { method = 'GET', body, json } = {}) {
    for (let attempt = 1; ; attempt++) {
      const response = await fetch(`${this.server}/api${path}`, {
        method,
        headers: { ...this.headers, ...(json === undefined ? {} : { 'Content-Type': 'application/json' }) },
        body: json === undefined ? body : JSON.stringify(json)
      })
      // Rate limited: the server says when to try again.
      if (response.status === 429 && attempt < 5) {
        const wait = Math.min(Number(response.headers.get('retry-after')) || 30, 120)
        console.log(`Rate limited by the server: retrying in ${wait}s`)
        await sleep(wait)
        continue
      }
      const text = await response.text()
      let parsed
      try {
        parsed = text ? JSON.parse(text) : null
      } catch {
        parsed = null
      }
      if (!response.ok) {
        let reason = message(parsed, `${response.status} ${response.statusText}`)
        if (response.status === 401 && !this.token) {
          reason += ' — no API token was given (a pull request from a fork gets no secrets)'
        }
        throw new Error(`${method} ${path}: ${reason}`)
      }
      return parsed
    }
  }

  async uploadAndScan(name, zip, health) {
    if (health.upload_store === 'local') {
      const form = new FormData()
      form.append('file', new Blob([zip], { type: 'application/zip' }), name)
      form.append('options', '{}')
      return await this.request('/scan/upload', { method: 'POST', body: form })
    }
    if (health.upload_store === 'blob') {
      const { upload } = await blobClient()
      const { folder } = await this.request('/scan/upload-folder')
      const blob = await upload(`${folder}${name}`, zip, {
        access: 'private',
        contentType: 'application/zip',
        handleUploadUrl: `${this.server}/api/scan/upload-token`,
        headers: this.headers
      })
      return await this.request('/scan', { method: 'POST', json: { upload: { pathname: blob.pathname, name } } })
    }
    throw new Error('This server doesn’t take uploads, so it can’t scan a repository’s skills')
  }

  async waitFor(id, deadline) {
    for (;;) {
      const scan = await this.request(`/scan/${encodeURIComponent(id)}`)
      if (scan.status === 'done' || scan.status === 'error') return scan
      if (Date.now() > deadline) throw new Error(`the scan didn’t finish in time (still ${scan.status})`)
      await sleep(POLL_SECONDS)
    }
  }
}

let blobModule
async function blobClient() {
  if (!blobModule) {
    const folder = join(env.RUNNER_TEMP || '/tmp', 'skillspector-action')
    mkdirSync(folder, { recursive: true })
    console.log(`Installing ${BLOB_PACKAGE} for the server's upload store`)
    execFileSync('npm', ['install', '--no-save', '--no-audit', '--no-fund', '--loglevel=error', '--prefix', folder, BLOB_PACKAGE], { stdio: 'inherit' })
    const entry = createRequire(join(folder, 'package.json')).resolve('@vercel/blob/client')
    blobModule = await import(pathToFileURL(entry).href)
  }
  return blobModule
}

class GitHub {
  constructor(token) {
    this.token = token
    this.api = env.GITHUB_API_URL || 'https://api.github.com'
    this.repo = env.GITHUB_REPOSITORY
  }

  async request(path, { method = 'GET', json } = {}) {
    const response = await fetch(`${this.api}${path}`, {
      method,
      headers: {
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
        ...(this.token ? { Authorization: `Bearer ${this.token}` } : {}),
        ...(json === undefined ? {} : { 'Content-Type': 'application/json' })
      },
      body: json === undefined ? undefined : JSON.stringify(json)
    })
    if (!response.ok) throw new Error(`GitHub ${method} ${path}: ${response.status} ${message(await response.json().catch(() => null), response.statusText)}`)
    return await response.json()
  }

  async list(path, pick = page => page) {
    const items = []
    for (let page = 1; ; page++) {
      const batch = pick(await this.request(`${path}${path.includes('?') ? '&' : '?'}per_page=100&page=${page}`))
      items.push(...batch)
      if (batch.length < 100) return items
    }
  }
}

// The files this run's event changed, or null when every skill should be scanned.
async function changedFiles(github, event, eventName) {
  const names = files => files.flatMap(file => [file.filename, file.previous_filename].filter(Boolean))
  if (event.pull_request) {
    const files = await github.list(`/repos/${github.repo}/pulls/${event.pull_request.number}/files`)
    return files.length >= PULL_FILES_LIMIT ? null : names(files)
  }
  if (eventName === 'push' && event.before && !/^0+$/.test(event.before) && event.after) {
    const { files = [] } = await github.request(`/repos/${github.repo}/compare/${event.before}...${event.after}`)
    return files.length >= COMPARE_FILES_LIMIT ? null : names(files)
  }
  return null
}

async function upsertComment(github, number, body, { create }) {
  const comments = await github.list(`/repos/${github.repo}/issues/${number}/comments`)
  const existing = comments.find(comment => comment.body?.includes(COMMENT_MARKER))
  if (existing) {
    await github.request(`/repos/${github.repo}/issues/comments/${existing.id}`, { method: 'PATCH', json: { body } })
  } else if (create) {
    await github.request(`/repos/${github.repo}/issues/${number}/comments`, { method: 'POST', json: { body } })
  }
}

function uploadName(skill) {
  const repo = (env.GITHUB_REPOSITORY || 'repository').split('/').pop()
  const name = skill === '.' ? repo : `${repo}-${skill.replaceAll('/', '-')}`
  return `${name.replace(/[^\w.\- ()]+/g, '_').slice(0, 96)}.zip`
}

async function scanSkill(server, health, workspace, skill, deadline) {
  const outcome = { skill }
  try {
    const zip = zipDirectory(join(workspace, skill))
    if (zip.length > health.max_upload_bytes) {
      throw new Error(`its zip is ${(zip.length / 1048576).toFixed(1)} MB, over the server’s ${Math.floor(health.max_upload_bytes / 1048576)} MB`)
    }
    const { id } = await server.uploadAndScan(uploadName(skill), zip, health)
    outcome.reportUrl = `${server.server}/scan/${id}`
    console.log(`Scanning ${skill}: ${outcome.reportUrl}`)
    const scan = await server.waitFor(id, deadline)
    if (scan.status === 'error') throw new Error(scan.error || 'the scan failed')
    outcome.risk = riskOf(scan.result)
    outcome.issues = issueCount(scan.result)
    outcome.sarif = await server.request(`/scan/${encodeURIComponent(id)}/export?format=sarif`)
  } catch (error) {
    outcome.error = error instanceof Error ? error.message : String(error)
  }
  return outcome
}

async function main() {
  const serverUrl = input('server-url')
  if (!serverUrl) throw new Error('server-url is required: the address of your Skillspector Web server')
  const roots = parseRoots(input('paths', '.'))
  const threshold = parseThreshold(input('fail-on', 'do-not-install'), input('max-risk-score'))
  const comment = input('comment', 'true') === 'true'
  const sarif = input('sarif', 'true') === 'true'
  const timeoutMinutes = Number(input('timeout-minutes', '20')) || 20
  const workspace = env.GITHUB_WORKSPACE || process.cwd()
  const eventName = env.GITHUB_EVENT_NAME || ''
  const event = env.GITHUB_EVENT_PATH ? JSON.parse(readFileSync(env.GITHUB_EVENT_PATH, 'utf8')) : {}

  const github = new GitHub(input('github-token'))
  const files = await changedFiles(github, event, eventName)
  const skills = files === null ? allSkills(roots, workspace) : changedSkills(files, roots, workspace)
  console.log(files === null
    ? `Scanning every skill under ${roots.join(', ')}: ${skills.length} found`
    : `${files.length} changed file${files.length === 1 ? '' : 's'}, in ${skills.length} skill${skills.length === 1 ? '' : 's'}`)

  const server = new Skillspector(serverUrl, input('token'))
  const outcomes = []
  if (skills.length) {
    const health = await server.request('/health')
    const deadline = Date.now() + timeoutMinutes * 60_000
    // One at a time: the server's rate limits and queue are per user.
    for (const skill of skills) {
      const outcome = await scanSkill(server, health, workspace, skill, deadline)
      outcome.failure = failureReason(outcome, threshold)
      if (outcome.error) console.log(`::error title=Skillspector::${skill} couldn’t be scanned: ${outcome.error}`)
      else if (outcome.failure) console.log(`::error title=Skillspector::${skill} fails the check: ${outcome.failure}`)
      else console.log(`${skill}: ${outcome.risk.recommendation}, risk score ${outcome.risk.score}`)
      outcomes.push(outcome)
    }
  }

  const summary = renderSummary(outcomes, { threshold })
  if (env.GITHUB_STEP_SUMMARY) appendFileSync(env.GITHUB_STEP_SUMMARY, `${summary}\n`)
  if (comment && event.pull_request) {
    try {
      // A pull request that touches no skill gets no comment, unless an earlier push left one.
      await upsertComment(github, event.pull_request.number, summary, { create: outcomes.length > 0 })
    } catch (error) {
      console.log(`::warning title=Skillspector::Couldn’t comment on the pull request (it needs pull-requests: write): ${error.message}`)
    }
  }

  const logs = outcomes.filter(outcome => outcome.sarif).map(outcome => repositorySarif(outcome.sarif, outcome.skill))
  if (sarif && logs.length) {
    const folder = join(env.RUNNER_TEMP || workspace, 'skillspector-sarif')
    mkdirSync(folder, { recursive: true })
    const file = join(folder, 'skillspector.sarif')
    writeFileSync(file, JSON.stringify(mergeSarif(logs), null, 2))
    setOutput('sarif-file', file)
  }

  const failed = outcomes.filter(outcome => outcome.failure)
  setOutput('scanned', String(outcomes.length))
  setOutput('failed', String(failed.length))
  setOutput('results', JSON.stringify(outcomes.map(({ skill, risk, issues, reportUrl, failure, error }) => ({
    skill,
    recommendation: risk?.recommendation ?? null,
    risk_score: risk?.score ?? null,
    issues: issues ?? null,
    report_url: reportUrl ?? null,
    failure: failure ?? null,
    error: error ?? null
  }))))
  if (failed.length) process.exitCode = 1
}

main().catch((error) => {
  console.log(`::error title=Skillspector::${error instanceof Error ? error.message : String(error)}`)
  process.exitCode = 1
})
