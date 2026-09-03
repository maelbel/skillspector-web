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
    apiBase: process.env.NUXT_API_BASE || 'http://localhost:8000'
  },

  compatibilityDate: '2026-09-03',

  vite: {
    server: {
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
