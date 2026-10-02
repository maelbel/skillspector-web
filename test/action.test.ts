import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, join } from 'node:path'
import { inflateRawSync } from 'node:zlib'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import {
  COMMENT_MARKER, allSkills, changedSkills, failureReason, issueCount, mergeSarif, parseRoots,
  parseThreshold, renderSummary, repositorySarif, riskOf
} from '../action/lib.mjs'
import { crc32, zipDirectory } from '../action/zip.mjs'

let workspace: string

function write(path: string, content = 'x') {
  mkdirSync(dirname(join(workspace, path)), { recursive: true })
  writeFileSync(join(workspace, path), content)
}

beforeEach(() => {
  workspace = mkdtempSync(join(tmpdir(), 'skillspector-action-'))
})

afterEach(() => {
  rmSync(workspace, { recursive: true, force: true })
})

// The archive's entries read back from its central directory, as an unzip tool would.
function unzip(zip: Buffer): Record<string, string> {
  const end = zip.lastIndexOf(Buffer.from([0x50, 0x4B, 0x05, 0x06]))
  const count = zip.readUInt16LE(end + 10)
  let at = zip.readUInt32LE(end + 16)
  const entries: Record<string, string> = {}
  for (let i = 0; i < count; i++) {
    expect(zip.readUInt32LE(at)).toBe(0x02014B50)
    const method = zip.readUInt16LE(at + 10)
    const crc = zip.readUInt32LE(at + 16)
    const size = zip.readUInt32LE(at + 20)
    const nameLength = zip.readUInt16LE(at + 28)
    const offset = zip.readUInt32LE(at + 42)
    const name = zip.subarray(at + 46, at + 46 + nameLength).toString('utf8')
    const start = offset + 30 + zip.readUInt16LE(offset + 26) + zip.readUInt16LE(offset + 28)
    const body = zip.subarray(start, start + size)
    const data = method === 8 ? inflateRawSync(body) : body
    expect(crc32(data)).toBe(crc)
    entries[name] = data.toString('utf8')
    at += 46 + nameLength
  }
  return entries
}

describe('parseRoots', () => {
  it('reads folders one per line or comma-separated, from the repository root', () => {
    expect(parseRoots('skills/\n ./more , skills')).toEqual(['skills', 'more'])
    expect(parseRoots('')).toEqual(['.'])
    expect(parseRoots('./')).toEqual(['.'])
  })

  it('refuses a folder outside the repository', () => {
    expect(() => parseRoots('../elsewhere')).toThrow(/isn't a folder of the repository/)
    expect(() => parseRoots('/etc')).toThrow(/isn't a folder of the repository/)
  })
})

describe('changedSkills', () => {
  beforeEach(() => {
    write('skills/pdf/SKILL.md')
    write('skills/pdf/scripts/run.sh')
    write('skills/docx/SKILL.md')
    write('README.md')
    write('other/SKILL.md')
  })

  it('finds the skill each changed file belongs to, once', () => {
    const files = ['skills/pdf/scripts/run.sh', 'skills/pdf/SKILL.md', 'skills/docx/SKILL.md', 'README.md']
    expect(changedSkills(files, ['skills'], workspace)).toEqual(['skills/docx', 'skills/pdf'])
  })

  it('skips a pull request that touches no skill', () => {
    expect(changedSkills(['README.md', 'skills/notes.txt'], ['skills'], workspace)).toEqual([])
  })

  it('ignores skills outside the paths, and deleted skills', () => {
    expect(changedSkills(['other/SKILL.md', 'skills/gone/SKILL.md'], ['skills'], workspace)).toEqual([])
    expect(changedSkills(['other/SKILL.md'], ['.'], workspace)).toEqual(['other'])
  })

  it('takes a skill at the root of the repository', () => {
    write('SKILL.md')
    expect(changedSkills(['README.md'], ['.'], workspace)).toEqual(['.'])
  })
})

describe('allSkills', () => {
  it('lists every folder with a SKILL.md under the paths', () => {
    write('skills/pdf/SKILL.md')
    write('skills/nested/deep/SKILL.md')
    write('skills/node_modules/dep/SKILL.md')
    write('other/SKILL.md')
    expect(allSkills(['skills'], workspace)).toEqual(['skills/nested/deep', 'skills/pdf'])
  })
})

describe('zipDirectory', () => {
  it('zips a skill with its files at the archive root, without .git', () => {
    write('skill/SKILL.md', '# Demo\n'.repeat(50))
    write('skill/scripts/run.sh', 'echo é')
    write('skill/.git/config', 'secret')
    expect(unzip(zipDirectory(join(workspace, 'skill')))).toEqual({
      'SKILL.md': '# Demo\n'.repeat(50),
      'scripts/run.sh': 'echo é'
    })
  })
})

describe('thresholds', () => {
  const outcome = (recommendation: string, score: number) => ({ skill: 's', risk: { recommendation, score } })

  it('fails on Do not install by default', () => {
    const threshold = parseThreshold('', '')
    expect(failureReason(outcome('DO_NOT_INSTALL', 91), threshold)).toBe('its verdict is “Do not install”')
    expect(failureReason(outcome('CAUTION', 50), threshold)).toBeNull()
  })

  it('fails on caution or worse, or on a risk score above the limit', () => {
    expect(failureReason(outcome('CAUTION', 50), parseThreshold('caution', ''))).toBe('its verdict is “Review before installing”')
    expect(failureReason(outcome('SAFE', 31), parseThreshold('never', '30'))).toBe('its risk score, 31, is above 30')
    expect(failureReason(outcome('SAFE', 30), parseThreshold('never', '30'))).toBeNull()
  })

  it('always fails a skill that couldn’t be scanned', () => {
    expect(failureReason({ skill: 's', error: 'boom' }, parseThreshold('never', ''))).toBe('it couldn’t be scanned')
  })

  it('refuses a threshold it doesn’t know', () => {
    expect(() => parseThreshold('sometimes', '')).toThrow(/fail-on/)
    expect(() => parseThreshold('never', '101')).toThrow(/max-risk-score/)
  })
})

describe('riskOf', () => {
  it('reads the report’s assessment, or the riskiest skill’s in a folder of several', () => {
    expect(riskOf({ risk_assessment: { score: 3 }, issues: [{}, {}] })).toEqual({ score: 3 })
    const several = { skills: [{ risk_assessment: { score: 10 }, issue_count: 1 }, { risk_assessment: { score: 70 }, issue_count: 2 }] }
    expect(riskOf(several)).toEqual({ score: 70 })
    expect(issueCount(several)).toBe(3)
  })
})

describe('repositorySarif', () => {
  const log = {
    version: '2.1.0',
    runs: [{
      tool: { driver: { name: 'skillspector' } },
      results: [{
        ruleId: 'SC2',
        locations: [{ physicalLocation: { artifactLocation: { uri: 'scripts/run.sh' } } }],
        relatedLocations: [{ physicalLocation: { artifactLocation: { uri: 'https://example.com/x.sh' } } }]
      }]
    }]
  }

  it('puts the files under the skill’s folder, with a category per skill', () => {
    const fixed = repositorySarif(log, 'skills/pdf')
    const run = fixed.runs[0]
    expect(run.results[0].locations[0].physicalLocation.artifactLocation.uri).toBe('skills/pdf/scripts/run.sh')
    expect(run.results[0].relatedLocations[0].physicalLocation.artifactLocation.uri).toBe('https://example.com/x.sh')
    expect(run.automationDetails).toEqual({ id: 'skillspector/skills/pdf/' })
    // The original is left as it was.
    expect(log.runs[0]!.results[0]!.locations[0]!.physicalLocation.artifactLocation.uri).toBe('scripts/run.sh')
  })

  it('merges every skill’s runs into one log', () => {
    const merged = mergeSarif([repositorySarif(log, 'a'), repositorySarif(log, '.')])
    expect(merged.runs.map((run: { automationDetails: { id: string } }) => run.automationDetails.id)).toEqual(['skillspector/a/', 'skillspector/root/'])
    expect(merged.runs[1].results[0].locations[0].physicalLocation.artifactLocation.uri).toBe('scripts/run.sh')
    expect(mergeSarif([])).toBeNull()
  })
})

describe('renderSummary', () => {
  const threshold = parseThreshold('do-not-install', '')

  it('has a row per skill, with its report, and says which failed', () => {
    const body = renderSummary([
      { skill: 'skills/pdf', risk: { recommendation: 'DO_NOT_INSTALL', score: 91 }, issues: 4, reportUrl: 'https://s.example/scan/1', failure: 'its verdict is “Do not install”' },
      { skill: 'skills/docx', risk: { recommendation: 'SAFE', score: 2 }, issues: 0, reportUrl: 'https://s.example/scan/2', failure: null },
      { skill: 'skills/x|y', error: 'the scan failed', failure: 'it couldn’t be scanned' }
    ], { threshold })
    expect(body.startsWith(COMMENT_MARKER)).toBe(true)
    expect(body).toContain('❌ 2 of 3 skills failed the check.')
    expect(body).toContain('| `skills/pdf` | 🔴 Do not install | 91/100 | 4 | [View report](https://s.example/scan/1) |')
    expect(body).toContain('| `skills/docx` | 🟢 Safe to install | 2/100 | 0 | [View report](https://s.example/scan/2) |')
    expect(body).toContain('| `skills/x\\|y` | ⚠️ Not scanned | — | — | — |')
    expect(body).toContain('- `skills/x\\|y` fails: it couldn’t be scanned (the scan failed).')
  })

  it('says when nothing was scanned', () => {
    expect(renderSummary([], { threshold })).toContain('changes no skill')
  })
})
