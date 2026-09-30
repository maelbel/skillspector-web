import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { describe, expect, it } from 'vitest'
import config, { BOTID_CHALLENGE, BOTID_PREFIX, BOTID_PROXY } from '../vercel'

// What botid's own integration rewrites: its Nuxt module lists the paths as proxy route rules.
const botidModule = readFileSync(createRequire(import.meta.url).resolve('botid/nuxt'), 'utf8')

describe('vercel.ts', () => {
  it('rewrites the paths botid loads its challenge from, to where botid expects', () => {
    expect(botidModule).toContain(`"${BOTID_PREFIX}/a-4-a/c.js"]={proxy:"${BOTID_CHALLENGE}"}`)
    expect(botidModule).toContain(`"${BOTID_PREFIX}/**"]={proxy:"${BOTID_PROXY}/**"`)
  })

  it('handles those paths at the edge, before the web service catches everything', () => {
    const sources = config.rewrites.map(rule => rule.source)

    expect(sources.at(-1)).toBe('/(.*)')
    expect(sources.slice(0, -1)).toEqual([`${BOTID_PREFIX}/a-4-a/c.js`, `${BOTID_PREFIX}/:path*`])
  })
})
