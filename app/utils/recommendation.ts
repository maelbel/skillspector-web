import type { Recommendation } from '~~/shared/types/scan'

export const RECOMMENDATION_LABEL: Record<Recommendation, string> = {
  SAFE: 'Safe to install',
  CAUTION: 'Review before installing',
  DO_NOT_INSTALL: 'Do not install'
}

// For tight spots: tables and the recent-scans list.
export const RECOMMENDATION_SHORT_LABEL: Record<Recommendation, string> = {
  SAFE: 'Safe',
  CAUTION: 'Review first',
  DO_NOT_INSTALL: 'Do not install'
}

export const RECOMMENDATION_ICON: Record<Recommendation, string> = {
  SAFE: 'i-lucide-shield-check',
  CAUTION: 'i-lucide-shield-alert',
  DO_NOT_INSTALL: 'i-lucide-shield-x'
}

// Written out in full so Tailwind can see every class.
export const RECOMMENDATION_CLASSES: Record<Recommendation, { dot: string, ink: string, chip: string, panel: string, rule: string }> = {
  SAFE: {
    dot: 'bg-safe',
    ink: 'text-safe-ink',
    chip: 'bg-safe-tint text-safe-ink ring-1 ring-safe-line',
    panel: 'bg-safe-tint border-safe-line',
    rule: 'border-safe-line'
  },
  CAUTION: {
    dot: 'bg-medium',
    ink: 'text-medium-ink',
    chip: 'bg-medium-tint text-medium-ink ring-1 ring-medium-line',
    panel: 'bg-medium-tint border-medium-line',
    rule: 'border-medium-line'
  },
  DO_NOT_INSTALL: {
    dot: 'bg-critical',
    ink: 'text-critical-ink',
    chip: 'bg-critical-tint text-critical-ink ring-1 ring-critical-line',
    panel: 'bg-critical-tint border-critical-line',
    rule: 'border-critical-line'
  }
}
