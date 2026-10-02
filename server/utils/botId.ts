import type { H3Event } from 'h3'
import { checkBotId } from 'botid/server'

// Refused submissions are reported to the API's monitoring (backend/app/monitoring.py), which
// alerts when every one is refused: a BotID misconfiguration looks like that, and no scan fails to
// show it. Batched per instance, so a flood of bots costs one call every few seconds.
const REPORT_EVERY_MS = 10_000
let unreported = 0
let lastReport = 0

async function reportRefusal(event: H3Event): Promise<void> {
  console.warn(JSON.stringify({ event: 'skillspector.bot_refused', at: Date.now() / 1000, path: event.path.split('?')[0] }))
  unreported++
  // CRON_SECRET authenticates the web app to the API's internal endpoints; it's set on hosted
  // servers, the only ones running BotID.
  const secret = process.env.CRON_SECRET
  if (!secret || Date.now() - lastReport < REPORT_EVERY_MS) return
  const count = unreported
  unreported = 0
  lastReport = Date.now()
  try {
    await $fetch('/internal/events', {
      baseURL: useRuntimeConfig(event).apiBase,
      method: 'POST',
      headers: { Authorization: `Bearer ${secret}` },
      body: { kind: 'bot_refused', count },
      timeout: 3000
    })
  } catch {
    unreported += count
  }
}

/** On the hosted version, refuse requests BotID classifies as bots (verified bots included: none
 * of them has a reason to start scans). Does nothing where BotID is off, or for a request with an
 * API token: a script is automated by design, and the API refuses a token that isn't valid. */
export async function refuseBots(event: H3Event): Promise<void> {
  if (!useRuntimeConfig(event).public.botid) return
  if (getApiToken(event)) return
  const verification = await checkBotId({ advancedOptions: { headers: event.node.req.headers } })
  if (verification.isBot) {
    await reportRefusal(event)
    throw createError({
      statusCode: 403,
      statusMessage: 'This request looked automated, so it was blocked. Reload the page and try again.'
    })
  }
}
