export default defineNuxtConfig({
  modules: [
    '@nuxt/eslint',
    '@nuxt/ui',
    '@nuxt/fonts'
  ],

  devtools: {
    enabled: true
  },

  app: {
    head: {
      link: [
        { rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' },
        { rel: 'icon', href: '/favicon.ico', sizes: '48x48' },
        { rel: 'apple-touch-icon', href: '/apple-touch-icon.png' }
      ]
    }
  },

  css: ['~/assets/css/main.css'],

  runtimeConfig: {
    apiBase: process.env.NUXT_API_BASE || 'http://localhost:8000',
    trustProxy: false
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
  },

  fonts: {
    defaults: {
      weights: [400, 500, 600],
      styles: ['normal']
    }
  }
})
