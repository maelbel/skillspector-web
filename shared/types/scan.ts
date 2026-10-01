export type JobStatus = 'pending' | 'running' | 'done' | 'error'

export type LLMProvider = 'anthropic' | 'openai' | 'azure_openai' | 'openai_compatible' | 'nv_build' | 'ollama' | 'claude_cli'

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
  // Set on findings in a referenced file the scan followed (skillspector's --transitive).
  source_url?: string | null
  transitive_depth?: number | null
  // Every place the rule matched; location is the first.
  occurrences?: { file: string, start_line: number, end_line: number | null }[]
  // Rule-specific detail, e.g. the file and reasons for a partly inspected one (AE1).
  evidence?: Record<string, unknown> | null
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
  // When the scan followed external references.
  transitive_targets_scanned?: number
  has_executable_scripts?: boolean
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

// A finding a baseline accepted: listed, but not counted in the score.
export type SuppressedFinding = Finding & { suppression_reason: string }

export interface BaselineDownload {
  filename: string
  content: string
}

// One skill of a repository holding several, as GET /api/scan/{id} lists it; its report comes from
// /api/scan/{id}/skills/{index}. Skills that failed only have `error`.
export interface SkillSummary {
  path: string
  name: string
  error?: string
  risk_assessment?: ScanReport['risk_assessment']
  issue_count?: number
  suppressed_count?: number
  execution_successful?: boolean
  ai_review?: AIReview | null
}

export interface UnscannedSkill {
  path: string
  name: string
  reason: string
}

// One file skillspector inspected.
export interface ScanComponent {
  path: string
  type: string
  lines: number | null
  executable: boolean
  size_bytes: number | null
  source_url?: string | null
}

// skillspector's summary of a structured skill bundle (protocol, declared tools, workflow…).
export interface StructuredSummary {
  id?: string
  message?: string
  file?: string
  [field: string]: unknown
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
  components?: ScanComponent[]
  structured_summaries?: StructuredSummary[]
  suppressed?: SuppressedFinding[]
  // A baseline accepting every active finding, made during the scan (app/sandbox_runner.py). Absent
  // without findings, and for scans from before it existed.
  generated_baseline?: Record<string, unknown>
  // A repository holding several skills: each one's summary, and those left out.
  skills?: SkillSummary[]
  unscanned_skills?: UnscannedSkill[]
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
