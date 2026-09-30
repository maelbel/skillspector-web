import type { H3Event } from 'h3'
import { checkBotId } from 'botid/server'

/** On the hosted version, refuse requests BotID classifies as bots (verified bots included: none
 * of them has a reason to start scans). Does nothing where BotID is off. */
export async function refuseBots(event: H3Event): Promise<void> {
  if (!useRuntimeConfig(event).public.botid) return
  const verification = await checkBotId({ advancedOptions: { headers: event.node.req.headers } })
  if (verification.isBot) {
    throw createError({
      statusCode: 403,
      statusMessage: 'This request looked automated, so it was blocked. Reload the page and try again.'
    })
  }
}
