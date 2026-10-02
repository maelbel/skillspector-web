// The operator's details for the legal pages (runtimeConfig.public.legal in nuxt.config.ts). The
// pages, and the links to them, exist only once a name and a contact email are set.
export function useLegal() {
  const legal = useRuntimeConfig().public.legal
  const enabled = !!(legal.operatorName && legal.contactEmail)
  return { legal, enabled }
}

export interface LegalFacts {
  hosted: boolean
  analytics: boolean
  speedInsights: boolean
  botProtection: boolean
  // Scans are kept until deleted when null.
  scanDays: number | null
  sessionDays: number
  activityDays: number
}

// What this server does with data, as the privacy policy describes it: read from its settings, so
// the policy stays true when they change.
export async function useLegalFacts(): Promise<ComputedRef<LegalFacts>> {
  const config = useRuntimeConfig().public
  const { data: health } = await useHealth()
  return computed(() => ({
    hosted: health.value?.mode === 'hosted',
    analytics: config.analytics,
    speedInsights: config.speedInsights,
    botProtection: config.botid,
    scanDays: health.value?.retention?.scan_days ?? null,
    sessionDays: health.value?.retention?.session_days ?? 30,
    activityDays: health.value?.retention?.activity_days ?? 365
  }))
}
