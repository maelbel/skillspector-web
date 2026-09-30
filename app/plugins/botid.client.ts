import { initBotId } from 'botid/client/core'

// Hosted only (see nuxt.config.ts): marks scan submissions so the server can tell people from bots.
export default defineNuxtPlugin({
  enforce: 'pre',
  setup() {
    if (!useRuntimeConfig().public.botid) return
    initBotId({ protect: [{ path: '/api/scan', method: 'POST' }] })
  }
})
