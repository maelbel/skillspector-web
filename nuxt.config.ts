// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  modules: [
    '@nuxt/eslint',
    '@nuxt/ui',
    '@nuxt/fonts'
  ],

  devtools: {
    enabled: true
  },

  css: ['~/assets/css/main.css'],

  runtimeConfig: {
    // Server-only: base URL of the FastAPI backend. Defaults to the
    // in-compose service name; override for local dev without Docker.
    apiBase: process.env.NUXT_API_BASE || 'http://localhost:8000'
  },

  compatibilityDate: '2026-09-03',

  vite: {
    server: {
      // Vite's dev server rejects unrecognized Host headers by default; the
      // production Docker target's plain Node server has no such check.
      allowedHosts: process.env.NUXT_ALLOWED_HOST ? [process.env.NUXT_ALLOWED_HOST] : []
    }
  },

  eslint: {
    config: {
      stylistic: {
        commaDangle: 'never',
        braceStyle: '1tbs'
      }
    }
  }
})
