export type JobStatus = 'pending' | 'running' | 'done' | 'error'

export type LLMProvider = 'anthropic' | 'openai' | 'ollama' | 'claude_cli'

export interface LLMConfig {
  provider: LLMProvider
  // Use the Claude key saved to the signed-in user's account instead of apiKey.
  useSavedKey?: boolean
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

// Whether a scan's AI review ran fully, partly or not at all (backend/app/ai_review.py); null for
// static scans.
export type AIReview = 'complete' | 'degraded' | 'failed'

// The parts of skillspector's report metadata the app reads. llm_provenance is skillspector 2.12+.
export interface ReportMetadata {
  llm_requested: boolean
  llm_available: boolean
  meta_analysis_applied: boolean
  llm_calls_attempted?: number
  llm_calls_succeeded?: number
  llm_degraded?: boolean
  llm_error?: string
  llm_provenance?: {
    provider: { configured_adapter: string }
    analyzers: { analyzer_id: string, model: string | null }[]
  }
}

// One gap in skillspector's inspection ledger: a file, or part of one, it couldn't fully check.
export interface LedgerException {
  outcome: string
  phase: string
  reason_code: string
  message?: string
  path?: string | null
  start_line?: number | null
  end_line?: number | null
  fatal?: boolean
  analyzers?: string[]
}

export interface AnalysisCompleteness {
  status: 'complete' | 'partial' | 'failed' | string
  is_complete: boolean
  execution_successful: boolean
  total_components?: number
  fully_inspected_files?: number
  partially_inspected_files?: number
  entirely_uninspected_files?: number
  ledger_exceptions?: LedgerException[]
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
  // Missing from reports stored before skillspector added them.
  metadata?: ReportMetadata
  analysis_completeness?: AnalysisCompleteness
}

export interface ScanStatus {
  id: string
  target: string
  status: JobStatus
  created_at: number
  finished_at: number | null
  result: ScanReport | null
  error: string | null
  ai_review: AIReview | null
  ai_tokens: AITokens | null
  completed_steps: number
  total_steps: number
}

// Tokens a scan's AI review used, as the provider reported them; null for counters it didn't report.
// `input` includes `cached`.
export interface AITokens {
  input: number | null
  output: number | null
  cached: number | null
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
  ai_review: AIReview | null
  completed_steps: number
  total_steps: number
}

export interface ScanHistoryResponse {
  items: ScanSummary[]
  total: number
}

export interface ScanLogsResponse {
  lines: string[]
}
