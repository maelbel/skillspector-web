import type { Recommendation } from '~~/shared/types/scan'

export const RECOMMENDATION_COLOR: Record<Recommendation, 'success' | 'warning' | 'error'> = {
  SAFE: 'success',
  CAUTION: 'warning',
  DO_NOT_INSTALL: 'error'
}

export const RECOMMENDATION_LABEL: Record<Recommendation, string> = {
  SAFE: 'Safe to install',
  CAUTION: 'Review before installing',
  DO_NOT_INSTALL: 'Do not install'
}

export const RECOMMENDATION_ICON: Record<Recommendation, string> = {
  SAFE: 'i-lucide-check-circle-2',
  CAUTION: 'i-lucide-alert-triangle',
  DO_NOT_INSTALL: 'i-lucide-shield-x'
}
