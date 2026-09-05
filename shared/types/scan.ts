export type JobStatus = 'pending' | 'running' | 'done' | 'error'

export type LLMProvider = 'anthropic' | 'openai' | 'ollama' | 'claude_cli'

export interface LLMConfig {
  provider: LLMProvider
  apiKey?: string
  baseUrl?: string
  model?: string
}

export type Severity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'

export type Recommendation = 'SAFE' | 'CAUTION' | 'DO_NOT_INSTALL'

export interface Finding {
  id: string
  finding_id: string
  category: string | null
  pattern: string | null
  severity: Severity
  confidence: number
  location: {
    file: string
    start_line: number
    end_line: number | null
  }
  finding: string | null
  explanation: string | null
  remediation: string | null
  code_snippet: string | null
  intent: string | null
  tags: string[]
}

export interface ScanReport {
  skill: {
    name: string
    source: string
    scanned_at: string
  }
  risk_assessment: {
    score: number
    severity: Severity
    recommendation: Recommendation
    max_issue_severity: Severity | 'NONE' | null
  }
  issues: Finding[]
  suppressed_count: number
  execution_successful: boolean
}

export interface ScanStatus {
  id: string
  target: string
  status: JobStatus
  created_at: number
  finished_at: number | null
  result: ScanReport | null
  error: string | null
  completed_steps: number
  total_steps: number
}

export interface ScanSummary {
  id: string
  target: string
  status: JobStatus
  created_at: number
  finished_at: number | null
  error: string | null
  risk_score: number | null
  severity: Severity | null
  recommendation: Recommendation | null
}

export interface ScanHistoryResponse {
  items: ScanSummary[]
  total: number
}

export interface ScanLogsResponse {
  lines: string[]
}
