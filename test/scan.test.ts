import { describe, expect, it } from 'vitest'
import { parseScanTarget } from '../shared/utils/scan'

describe('parseScanTarget', () => {
  it('shortens a GitHub repo URL to owner/repo', () => {
    expect(parseScanTarget('https://github.com/NVIDIA/skillspector.git')).toEqual({ title: 'NVIDIA/skillspector', isGithub: true })
  })

  it('keeps the path of a GitHub tree or blob URL, without the ref', () => {
    expect(parseScanTarget('https://github.com/acme/skills/tree/main/pdf/SKILL.md')).toEqual({ title: 'acme/skills/pdf/SKILL.md', isGithub: true })
  })

  it('keeps the path of a raw.githubusercontent.com URL, without the ref', () => {
    expect(parseScanTarget('https://raw.githubusercontent.com/acme/skills/main/pdf/SKILL.md')).toEqual({ title: 'acme/skills/pdf/SKILL.md', isGithub: true })
  })

  it('leaves other URLs and GitHub URLs without a repo untouched', () => {
    expect(parseScanTarget('https://example.com/skill.zip')).toEqual({ title: 'https://example.com/skill.zip', isGithub: false })
    expect(parseScanTarget('https://github.com/acme')).toEqual({ title: 'https://github.com/acme', isGithub: false })
  })

  it('returns unparseable input as-is', () => {
    expect(parseScanTarget('not a url')).toEqual({ title: 'not a url', isGithub: false })
  })
})
