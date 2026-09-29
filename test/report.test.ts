import { describe, expect, it } from 'vitest'
import type { Finding } from '../shared/types/scan'
import { findingKey, findingLocation, findingTitle, formatDuration, groupCompletedStages, scanDurationSeconds } from '../shared/utils/report'

function finding(overrides: Partial<Finding> = {}): Finding {
  return {
    id: 'E1',
    finding_id: 'finding-1',
    category: 'Data Exfiltration',
    pattern: 'External Transmission',
    severity: 'MEDIUM',
    confidence: 0.5,
    location: { file: 'SKILL.md', start_line: 64, end_line: null },
    finding: 'https://api.github.com/',
    explanation: 'Data is being sent to an external URL.',
    remediation: null,
    code_snippet: null,
    intent: null,
    tags: [],
    ...overrides
  }
}

describe('groupCompletedStages', () => {
  it('counts completed steps per analyzer family, in scan order', () => {
    const lines = [
      'Starting scan of https://github.com/acme/skill',
      'resolve_input completed',
      'static_patterns_ssrf completed',
      'WARNING something odd',
      'static_patterns_anti_refusal completed',
      'mcp_rug_pull completed',
      'static_yara completed',
      'report completed'
    ]
    expect(groupCompletedStages(lines)).toEqual([
      { label: 'Fetch & prepare', completed: 1 },
      { label: 'Static patterns', completed: 2 },
      { label: 'YARA signatures', completed: 1 },
      { label: 'MCP tool checks', completed: 1 },
      { label: 'Integrity & scoring', completed: 1 }
    ])
  })

  it('returns nothing before any step completes', () => {
    expect(groupCompletedStages(['Starting scan of x'])).toEqual([])
  })
})

describe('findingTitle', () => {
  it('prefers the rule name over the matched text', () => {
    expect(findingTitle(finding())).toBe('External Transmission')
  })

  it('falls back to the category, then the explanation', () => {
    expect(findingTitle(finding({ pattern: null }))).toBe('Data Exfiltration')
    expect(findingTitle(finding({ pattern: null, category: null }))).toBe('Data is being sent to an external URL.')
  })
})

describe('findingKey', () => {
  it('tells apart occurrences that share a finding_id', () => {
    const a = finding()
    const b = finding({ location: { file: 'SKILL.md', start_line: 253, end_line: null } })
    expect(findingKey(a)).not.toBe(findingKey(b))
  })
})

describe('findingLocation', () => {
  it('shows a line range only when it spans several lines', () => {
    expect(findingLocation(finding())).toBe('SKILL.md:64')
    expect(findingLocation(finding({ location: { file: 'a.py', start_line: 3, end_line: 7 } }))).toBe('a.py:3–7')
    expect(findingLocation(finding({ location: { file: 'a.py', start_line: 0, end_line: null } }))).toBe('a.py')
  })
})

describe('scan duration', () => {
  it('is null while the scan runs, then rounded seconds', () => {
    expect(scanDurationSeconds({ created_at: 100, finished_at: null })).toBeNull()
    expect(scanDurationSeconds({ created_at: 100, finished_at: 114.6 })).toBe(15)
  })

  it('formats seconds and minutes', () => {
    expect(formatDuration(14)).toBe('14 s')
    expect(formatDuration(120)).toBe('2 min')
    expect(formatDuration(75)).toBe('1 min 15 s')
  })
})
