import type { Severity } from '~~/shared/types/scan'

export const SEVERITY_LABEL: Record<Severity, string> = {
  CRITICAL: 'Critical',
  HIGH: 'High',
  MEDIUM: 'Medium',
  LOW: 'Low'
}

export const SEVERITIES: Severity[] = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']

export const SEVERITY_RANK: Record<Severity, number> = {
  CRITICAL: 0,
  HIGH: 1,
  MEDIUM: 2,
  LOW: 3
}

// Written out in full so Tailwind can see every class.
export const SEVERITY_CLASSES: Record<Severity, { dot: string, ink: string, chip: string }> = {
  CRITICAL: { dot: 'bg-critical', ink: 'text-critical-ink', chip: 'bg-critical-tint text-critical-ink' },
  HIGH: { dot: 'bg-high', ink: 'text-high-ink', chip: 'bg-high-tint text-high-ink' },
  MEDIUM: { dot: 'bg-medium', ink: 'text-medium-ink', chip: 'bg-medium-tint text-medium-ink' },
  LOW: { dot: 'bg-low', ink: 'text-low-ink', chip: 'bg-low-tint text-low-ink' }
}
