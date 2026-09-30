import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { describe, expect, it } from 'vitest'
import config from '../vercel'

// What botid's own integration rewrites: its Nuxt module lists the paths as proxy route rules.
const botidModule = readFileSync(createRequire(import.meta.url).resolve('botid/nuxt'), 'utf8')
const proxied = [...botidModule.matchAll(/"([^"]+)"\]=\{proxy:"([^"]+)"/g)].map(([, source, destination]) => ({
  source: source!.replace(/\/\*\*$/, '/:path*'),
  destination: destination!.replace(/\/\*\*$/, '/:path*')
}))

describe('vercel.ts', () => {
  it('rewrites the paths botid loads its challenge from, to where botid expects', () => {
    expect(proxied).toHaveLength(2)
    expect(config.rewrites.slice(0, -1)).toEqual(proxied)
  })

  it('handles those paths at the edge, before the web service catches everything', () => {
    expect(config.rewrites.at(-1)).toEqual({ source: '/(.*)', destination: { service: 'web' } })
  })
})
