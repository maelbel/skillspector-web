<script setup lang="ts">
// The terms of use in English (app/pages/terms.vue); TermsFr.vue says the same in French.
const { legal } = useLegal()
const { site } = useAppConfig()
</script>

<template>
  <section>
    <h2>The service</h2>
    <p>
      This server, run by {{ legal.operatorName }}, checks AI agent skills and MCP servers for security
      risks before you install them: it scans what you submit with
      <a
        :href="`https://github.com/${site.scannerRepo}`"
        target="_blank"
        rel="noopener"
      >skillspector</a>, and, if you ask, has an AI model review it. Using it means accepting these
      terms. The software is open source, under the MIT licence; these terms are about this server.
    </p>
  </section>

  <section>
    <h2>Your account</h2>
    <ul>
      <li>An account is for one person. Give an email address you can receive mail at.</li>
      <li>
        Keep your password, API tokens and keys to yourself: you’re responsible for what’s done with
        them. Revoke a token or change your password as soon as you think it leaked.
      </li>
      <li>You can delete your account at any time, from your Account page.</li>
    </ul>
  </section>

  <section>
    <h2>Acceptable use</h2>
    <p>
      Submitting suspicious skills to have them checked is what the service is for. Using it against
      the service, its providers or anyone else is not. In particular, don’t:
    </p>
    <ul>
      <li>submit content you have no right to access or have analysed;</li>
      <li>
        try to get around the quotas, rate limits or bot protection, for example with several accounts,
        or overload the server;
      </li>
      <li>
        try to reach other users’ data, the server’s secrets or systems, or use scans to reach other
        systems than the code hosts they’re meant for;
      </li>
      <li>
        use the service for anything unlawful, or put personal data or secrets of others in what you
        submit without reason.
      </li>
    </ul>
    <p>
      Found a vulnerability? Please report it privately to
      <a :href="`mailto:${legal.contactEmail}`">{{ legal.contactEmail }}</a> rather than exploit it.
    </p>
  </section>

  <section>
    <h2>Quotas</h2>
    <p>
      The operator can limit how many scans each account starts a day and runs at once, and how often
      requests can be made. Your Account page shows your current limits. They can change, and scans
      can be paused for everyone, for example during an incident.
    </p>
  </section>

  <section>
    <h2>Results are advice, not a guarantee</h2>
    <p>
      Scans are automated, by static analysis and, when you turn it on, an AI model. They can miss a
      real threat and flag harmless code. A “safe” verdict means nothing alarming was found, not that
      the skill is safe. You remain responsible for what you install and run: read a skill’s code, and
      weigh a result with your own judgement, before trusting it.
    </p>
  </section>

  <section>
    <h2>What you submit</h2>
    <ul>
      <li>
        You keep all your rights over what you submit. You allow the operator to fetch, store and
        analyse it, and to show the results to you and to whoever you share them with, only to provide
        the service.
      </li>
      <li>
        With AI review on, the skill’s content is sent to the AI provider you chose, under its own
        terms.
      </li>
      <li>
        A result you share, or put on a badge, is public: make sure you may publish it, especially for a
        private repository.
      </li>
    </ul>
  </section>

  <section>
    <h2>Availability</h2>
    <p>
      The service is provided as it is, without any guarantee of availability. A scan can fail or time
      out. The operator can change it, suspend it or end it, and will try to give notice of an end, so
      you can download your reports.
    </p>
  </section>

  <section>
    <h2>Liability</h2>
    <p>
      As far as the law allows, the operator isn’t liable for indirect damage, or for losses from
      relying on a result, a scan that failed, or the service being unavailable. Nothing in these terms
      limits liability that the law doesn’t allow to be limited, nor the rights consumers have under
      the law.
    </p>
  </section>

  <section>
    <h2>Suspension</h2>
    <p>
      The operator can suspend or delete an account that breaks these terms, after telling its owner
      why where possible, or at once for a serious breach such as an attack on the service.
    </p>
  </section>

  <section>
    <h2>Changes and law</h2>
    <p>
      These terms change when the service does; the date at the top says when they last did, and using
      the service afterwards means accepting them.<template v-if="legal.governingLaw">
        They’re governed
        by {{ legal.governingLaw }}.
      </template> Questions:
      <a :href="`mailto:${legal.contactEmail}`">{{ legal.contactEmail }}</a>.
    </p>
  </section>
</template>
