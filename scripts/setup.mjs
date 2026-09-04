#!/usr/bin/env node
// Interactive project setup: `pnpm setup`. Wires up backend/.env.local and,
// depending on the chosen mode, either `uv sync`s the backend or brings up
// docker compose.
import { randomBytes } from 'node:crypto'
import { spawnSync } from 'node:child_process'
import { existsSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import * as p from '@clack/prompts'

const rootDir = dirname(dirname(fileURLToPath(import.meta.url)))
const backendDir = join(rootDir, 'backend')
const envExamplePath = join(backendDir, '.env.example')
const envLocalPath = join(backendDir, '.env.local')

function commandExists(cmd) {
  return spawnSync(cmd, ['--version'], { stdio: 'ignore' }).error === undefined
}

function run(label, cmd, args, cwd) {
  const spinner = p.spinner()
  spinner.start(label)
  const result = spawnSync(cmd, args, { cwd, encoding: 'utf8' })
  if (result.status !== 0) {
    spinner.stop(`${label} — failed`, 1)
    p.log.error(result.stderr || result.stdout || `${cmd} exited with ${result.status}`)
    return false
  }
  spinner.stop(label)
  return true
}

function parseEnvExample(path) {
  return readFileSync(path, 'utf8')
    .split('\n')
    .filter(line => line.includes('='))
    .map((line) => {
      const index = line.indexOf('=')
      return [line.slice(0, index), line.slice(index + 1)]
    })
}

async function main() {
  console.clear()
  p.intro('skillspector-web setup')

  const mode = await p.select({
    message: 'How do you want to run this locally?',
    options: [
      { value: 'docker', label: 'Docker Compose (recommended)', hint: 'one command, matches production' },
      { value: 'local', label: 'Local processes', hint: 'uv + pnpm dev, two terminals' }
    ]
  })
  if (p.isCancel(mode)) return p.cancel('Setup cancelled.')

  // --- backend/.env.local -------------------------------------------------
  let writeEnv = true
  if (existsSync(envLocalPath)) {
    const overwrite = await p.confirm({
      message: 'backend/.env.local already exists — overwrite it?',
      initialValue: false
    })
    if (p.isCancel(overwrite)) return p.cancel('Setup cancelled.')
    writeEnv = overwrite
  }

  if (writeEnv) {
    const defaults = Object.fromEntries(parseEnvExample(envExamplePath))

    const corsOrigins = await p.text({
      message: 'Origins allowed to call the API (CORS)',
      initialValue: defaults.SKILLSPECTOR_WEB_CORS_ORIGINS || '["http://localhost:3000"]'
    })
    if (p.isCancel(corsOrigins)) return p.cancel('Setup cancelled.')

    const maxConcurrentScans = await p.text({
      message: 'Max concurrent scans',
      initialValue: defaults.SKILLSPECTOR_WEB_MAX_CONCURRENT_SCANS || '2',
      validate: value => (/^\d+$/.test(value) ? undefined : 'Enter a whole number')
    })
    if (p.isCancel(maxConcurrentScans)) return p.cancel('Setup cancelled.')

    const adminTokenChoice = await p.select({
      message: 'Admin token (gates the Claude CLI login endpoint)',
      options: [
        { value: 'generate', label: 'Generate a random token' },
        { value: 'blank', label: 'Leave blank', hint: 'disables the login endpoint' },
        { value: 'custom', label: 'Enter my own' }
      ]
    })
    if (p.isCancel(adminTokenChoice)) return p.cancel('Setup cancelled.')

    let adminToken = ''
    if (adminTokenChoice === 'generate') {
      adminToken = randomBytes(24).toString('hex')
    } else if (adminTokenChoice === 'custom') {
      const custom = await p.text({ message: 'Admin token' })
      if (p.isCancel(custom)) return p.cancel('Setup cancelled.')
      adminToken = custom
    }

    const envContents = [
      `SKILLSPECTOR_WEB_CORS_ORIGINS=${corsOrigins}`,
      `SKILLSPECTOR_WEB_MAX_CONCURRENT_SCANS=${maxConcurrentScans}`,
      `SKILLSPECTOR_WEB_ADMIN_TOKEN=${adminToken}`,
      ''
    ].join('\n')
    writeFileSync(envLocalPath, envContents)
    p.log.success('Wrote backend/.env.local')

    if (adminTokenChoice === 'generate') {
      p.note(adminToken, 'Admin token (save this — needed for the /admin/claude-login flow)')
    }
  } else {
    p.log.info('Keeping existing backend/.env.local')
  }

  // --- mode-specific steps -------------------------------------------------
  if (mode === 'docker') {
    if (!commandExists('docker')) {
      p.log.error('docker was not found on PATH — install Docker, then run `docker compose up --build`.')
    } else {
      const bringUp = await p.confirm({
        message: 'Run `docker compose up --build -d` now?',
        initialValue: true
      })
      if (!p.isCancel(bringUp) && bringUp) {
        run('Building and starting containers', 'docker', ['compose', 'up', '--build', '-d'], rootDir)
      }
    }
    p.outro([
      'Frontend: http://localhost:3005',
      'Optional Claude CLI provider login: docker exec -it skillspector-api claude auth login'
    ].join('\n'))
    return
  }

  // mode === 'local'
  if (!commandExists('uv')) {
    p.log.error('uv was not found on PATH — install it (https://docs.astral.sh/uv/) and re-run `pnpm setup`.')
  } else {
    run('Installing backend dependencies (uv sync)', 'uv', ['sync'], backendDir)
  }

  p.outro([
    'Start the backend:  cd backend && uv run uvicorn app.main:app --reload',
    'Start the frontend: NUXT_API_BASE=http://localhost:8000 pnpm dev',
    'Then open http://localhost:3000'
  ].join('\n'))
}

main()
