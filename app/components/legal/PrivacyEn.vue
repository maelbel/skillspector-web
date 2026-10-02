<script setup lang="ts">
// The privacy policy in English (app/pages/privacy.vue); PrivacyFr.vue says the same in French.
// What it says about this server comes from its settings (useLegalFacts).
import type { LegalFacts } from '~/composables/useLegal'

defineProps<{ facts: LegalFacts }>()
const { legal } = useLegal()

const days = (count: number) => `${count} day${count === 1 ? '' : 's'}`
</script>

<template>
  <section>
    <h2>Who is responsible</h2>
    <p>
      {{ legal.operatorName }} runs this server and is responsible for the personal data it processes
      (the data controller). For any question about your data, or to exercise your rights, write to
      <a :href="`mailto:${legal.contactEmail}`">{{ legal.contactEmail }}</a>.
    </p>
  </section>

  <section>
    <h2>What is kept, and why</h2>
    <h3>Your account</h3>
    <ul>
      <li>
        Your email address, your password (only as a scrypt hash, which can’t be turned back into it),
        your role, when the account was created and when you last signed in. They’re needed to give
        you an account (the contract between you and the operator).
      </li>
      <li>
        Your sign-in session: a random token in a cookie, <code>skillspector_session</code>, kept
        {{ days(facts.sessionDays) }} or until you sign out. It’s needed for the site to work, so it
        doesn’t need your consent.<template v-if="facts.botProtection">
          Vercel BotID, which protects
          the scan form from automated abuse, sets its own security cookies (named
          <code>KP_…</code>).
        </template> There are no advertising or tracking cookies.
      </li>
      <li>
        If you create them: your API tokens (their name and when they were last used; the token itself
        only as a hash), your Claude key (encrypted with AES-256-GCM, only ever used for your own scans,
        and shown back only as its last characters), and your GitHub connection (your GitHub username,
        and its access tokens, encrypted, used only to read the repositories you chose, for your scans).
      </li>
    </ul>
    <h3>Your scans</h3>
    <ul>
      <li>
        What you submit to be scanned (a link, a skill’s name in a registry, or a file), the options
        you chose, the report, the scan’s log, and how many AI tokens it used. They’re needed to give
        you the service. Your scans are private to you unless you share them.
      </li>
      <li>
        An uploaded file is deleted as soon as it has been scanned, whatever the outcome; only its
        name stays in your history.
      </li>
      <li>
        A key you paste for one scan, instead of saving it, is held only while that scan runs{{ facts.hosted ? ', encrypted, and deleted once it has run' : '' }}.
      </li>
    </ul>
    <h3>Security</h3>
    <ul>
      <li>
        An activity log of events on accounts: sign-ups, password changes and resets, API tokens,
        Claude keys and GitHub connections being added or removed, results being shared or put on a
        badge, and what admins change. It’s kept {{ days(facts.activityDays) }}, to investigate abuse
        or a security incident (the operator’s legitimate interest in keeping the service safe).
      </li>
      <li>
        Your IP address, to limit how often sign-ins, scans and shared pages can be requested, which
        stops abuse.
        <template v-if="facts.hosted">
          It’s stored only for the length of the limit it counts towards, at most 5 minutes.
        </template>
        <template v-else>
          It’s held in this server’s memory only, for at most 5 minutes.
        </template>
        The host also records requests, with their IP address, in its own logs.
      </li>
      <li v-if="facts.botProtection">
        When you submit a scan, Vercel BotID checks that the request comes from a browser rather than
        an automated script.
      </li>
    </ul>
    <template v-if="facts.analytics || facts.speedInsights">
      <h3>Audience measurement</h3>
      <ul>
        <li v-if="facts.analytics">
          Vercel Web Analytics counts visits without cookies. It receives the kind of page visited,
          never its address (which can hold a scan or a shared link), and three events: an account
          being created, a scan being started (whether it was a link, an upload, a GitHub repository
          or an MCP server, and whether AI review was on) and a result being viewed (its verdict).
          Never what was scanned, your email or any identifier.
        </li>
        <li v-if="facts.speedInsights">
          Vercel Speed Insights measures how fast pages load, with the same page kinds.
        </li>
        <li>This helps the operator see how the service is used and improve it (legitimate interest).</li>
      </ul>
    </template>
    <h3>In your browser</h3>
    <p>
      The scan form remembers your last choices (the source, whether AI review was on, the provider
      and model, never a key), and the site remembers your light or dark theme, in your browser’s
      local storage. It never leaves your browser.
    </p>
  </section>

  <section>
    <h2>What is public</h2>
    <p>
      Nothing, unless you make it so. A result you share can be opened by anyone with its link, which
      shows the report, not who scanned it, until you revoke it. A result you put on a status badge
      shows its verdict to anyone who views the badge.
    </p>
  </section>

  <section>
    <h2>Who else receives it</h2>
    <ul>
      <li v-if="legal.hostName">
        {{ legal.hostName }}, which hosts the server{{ facts.hosted ? ', stores uploaded files until they’re scanned, and runs each scan in an isolated sandbox' : '' }}.
      </li>
      <li v-if="legal.databaseProvider">
        {{ legal.databaseProvider }}, which hosts the database.
      </li>
      <li v-if="legal.emailProvider">
        {{ legal.emailProvider }}, which sends password reset emails.
      </li>
      <li>
        The AI provider you choose, only when you turn on AI review for a scan: it receives the content
        of the skill being scanned{{ facts.hosted ? ' (Anthropic, with your own key)' : '' }},
        under its own terms.
      </li>
      <li>
        GitHub, if you connect your account, to read the repositories you chose. The code hosts of the
        links you scan see the server fetch them, not you.
      </li>
      <li>
        The admins of this server, who can see accounts’ email addresses and API token names, scans
        (not the content of a scan of a private repository) and the activity log, to run the service.
      </li>
    </ul>
    <p>
      Your data is never sold, and never used for advertising. Some of these providers are based in, or
      process data in, the United States; transfers there rely on the safeguards the GDPR provides, such
      as the EU–US Data Privacy Framework or the European Commission’s standard contractual clauses.
    </p>
  </section>

  <section>
    <h2>How long it’s kept</h2>
    <ul>
      <li>
        Your account, its keys, tokens and connections: until you delete it, or an admin does.
      </li>
      <li>
        Your scans:
        <template v-if="facts.scanDays !== null">
          {{ days(facts.scanDays) }}, or less if you delete them or your account first.
        </template>
        <template v-else>
          until you delete them or your account.
        </template>
      </li>
      <li>Sessions: {{ days(facts.sessionDays) }}, or until you sign out.</li>
      <li>Password reset links: 24 hours, or until they’re used.</li>
      <li>The activity log: {{ days(facts.activityDays) }}.</li>
      <li>Uploaded files: until they’re scanned, usually a few minutes; 7 hours at most if a scan never runs.</li>
      <li>IP addresses for rate limits: at most 5 minutes.</li>
    </ul>
    <p v-if="facts.hosted">
      Database backups made by the hosting providers can hold deleted data a little longer, until they
      expire.
    </p>
  </section>

  <section>
    <h2>Your rights</h2>
    <p>
      Under the GDPR, you can access your data, have it corrected or deleted, restrict or object to its
      processing, and receive it in a portable format.
    </p>
    <ul>
      <li>
        <strong>Delete your account</strong> yourself, from your Account page: your scans and their
        reports, shared links and badges, keys, tokens and connections are deleted at once, and the
        activity log keeps its entries without your email.
      </li>
      <li>Delete a scan from its result page, and download any report there.</li>
      <li>
        For anything else, write to <a :href="`mailto:${legal.contactEmail}`">{{ legal.contactEmail }}</a>.
        You’ll get an answer within a month.
      </li>
    </ul>
    <p>
      If you think your data isn’t handled properly, you can complain to
      {{ legal.supervisoryAuthority || 'the data protection authority of the country you live in' }}.
    </p>
  </section>

  <section>
    <h2>How it’s protected</h2>
    <p>
      Passwords are hashed, keys and tokens are encrypted or hashed, connections use HTTPS, and the
      session cookie can’t be read by scripts on the page.<template v-if="facts.hosted">
        Scans run
        in a sandbox that holds none of the server’s secrets.
      </template>
    </p>
  </section>

  <section>
    <h2>Changes</h2>
    <p>
      This policy changes when the service does. The date at the top says when it last did.
    </p>
  </section>
</template>
