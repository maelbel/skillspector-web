import { describe, expect, it } from 'vitest'
import { describeScanTarget, parseScanTarget } from '../shared/utils/scan'

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

describe('describeScanTarget', () => {
  it('ignores empty input', () => {
    expect(describeScanTarget('   ')).toBeNull()
  })

  it.each([
    ['https://github.com/acme/skills', 'repository', 'GitHub', 'acme/skills'],
    ['https://gitlab.com/acme/skills.git', 'repository', 'GitLab', 'https://gitlab.com/acme/skills.git'],
    ['https://github.com/acme/skills/blob/main/pdf/SKILL.md', 'file', 'GitHub', 'acme/skills/pdf/SKILL.md'],
    ['https://raw.githubusercontent.com/acme/skills/main/pdf/SKILL.md', 'file', 'GitHub', 'acme/skills/pdf/SKILL.md'],
    ['https://github.com/acme/skills/archive/refs/heads/main.zip', 'archive', 'GitHub', 'acme/skills'],
    ['https://huggingface.co/acme/skill/resolve/main/skill.zip', 'archive', 'Hugging Face', 'https://huggingface.co/acme/skill/resolve/main/skill.zip']
  ])('accepts %s as a %s on %s', (target, kind, host, title) => {
    expect(describeScanTarget(target)).toEqual({ ok: true, kind, host, title })
  })

  it.each([
    ['github.com/acme/skills', 'full URL'],
    ['http://github.com/acme/skills', 'https://'],
    ['https://example.com/skill.zip', 'GitHub, GitLab, Bitbucket or Hugging Face'],
    ['https://github.com/acme/skills/tree/main/pdf', 'Folder links'],
    ['https://github.com/acme', 'Link to a repository']
  ])('rejects %s', (target, problem) => {
    const info = describeScanTarget(target)
    expect(info?.ok).toBe(false)
    expect(info && !info.ok && info.problem).toContain(problem)
  })
})
