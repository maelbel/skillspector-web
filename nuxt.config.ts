// BotID (Vercel bot detection) guards scan submissions on the hosted version only. It needs
// Vercel's edge, which vercel.ts routes its challenge through, so self-hosted builds leave it out.
// Read at build time and at runtime.
const botId = process.env.NUXT_PUBLIC_BOTID === 'true'
// Vercel Web Analytics (app/analytics/vercel.client.ts), on the hosted version too. Read at build
// time only: without it the plugin isn't built in, so self-hosted pages never load Vercel's script.
const analytics = process.env.NUXT_PUBLIC_ANALYTICS === 'true'
// Vercel Speed Insights (app/analytics/speed-insights.client.ts): the same, for Core Web Vitals.
const speedInsights = process.env.NUXT_PUBLIC_SPEED_INSIGHTS === 'true'

export default defineNuxtConfig({
  modules: [
    '@nuxt/eslint',
    '@nuxt/ui',
    '@nuxt/fonts'
  ],

  plugins: [
    ...(analytics ? ['~/analytics/vercel.client'] : []),
    ...(speedInsights ? ['~/analytics/speed-insights.client'] : [])
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
    trustProxy: false,
    public: {
      botid: botId,
      // This server's public address, e.g. https://skillspector.example.com, for the link preview
      // image's absolute URL (useSiteUrl). Unset, it's the address each page was requested at.
      siteUrl: '',
      // Whether this build sends Web Analytics and Speed Insights, for the privacy policy to say so.
      analytics,
      speedInsights,
      // The operator behind this server, for the legal notice, privacy policy and terms (app/pages/
      // legal.vue, privacy.vue, terms.vue). Set at runtime as NUXT_PUBLIC_LEGAL_<FIELD>, e.g.
      // NUXT_PUBLIC_LEGAL_OPERATOR_NAME. The pages exist only once a name and a contact email are set.
      legal: {
        // Who runs the server: a person's name, or a company's.
        operatorName: '',
        // A company's legal form, registration (RCS, SIREN) and share capital, or VAT number.
        operatorDetails: '',
        operatorAddress: '',
        contactEmail: '',
        // Who is responsible for the site's content (France: directeur de la publication).
        publicationDirector: '',
        // Who hosts it, e.g. Vercel Inc., 440 N Barranca Avenue #4133, Covina, CA 91723, United States.
        hostName: '',
        hostAddress: '',
        // Its phone number or contact page.
        hostContact: '',
        // Who stores the database and sends emails, when that's not the host, e.g. Neon, Mailgun.
        databaseProvider: '',
        emailProvider: '',
        // The data protection authority users can complain to, e.g. the CNIL (https://www.cnil.fr),
        // and the same in French for the French pages (the English one when unset).
        supervisoryAuthority: '',
        supervisoryAuthorityFr: '',
        // The law and courts that apply to the terms, e.g. French law and the courts of Paris; and in
        // French, e.g. le droit français et les tribunaux de Paris.
        governingLaw: '',
        governingLawFr: '',
        // When the pages were last changed, shown on each (YYYY-MM-DD).
        updatedAt: ''
      }
    }
  },

  routeRules: {
    // The link preview image (app.config.ts): cached a year, so it's renamed when it changes.
    '/og-image.png': { headers: { 'cache-control': 'public, max-age=31536000, immutable' } }
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
      weights: [400, 500, 600, 700, 800],
      styles: ['normal']
    }
  }
})
