<script setup lang="ts">
const { legal } = useLegal()
const { site } = useAppConfig()
</script>

<template>
  <LegalPage
    v-slot="{ fr }"
    title="Legal notice"
    lead="Who runs this server, and who hosts it."
    title-fr="Mentions légales"
    lead-fr="Qui exploite ce serveur, et qui l’héberge."
  >
    <section>
      <h2>{{ fr ? 'Éditeur' : 'Operator' }}</h2>
      <dl>
        <dt>{{ fr ? 'Édité par' : 'Operated by' }}</dt>
        <dd>{{ legal.operatorName }}</dd>
        <template v-if="legal.operatorDetails">
          <dt>{{ fr ? 'Immatriculation' : 'Registration' }}</dt>
          <dd>{{ legal.operatorDetails }}</dd>
        </template>
        <template v-if="legal.operatorAddress">
          <dt>{{ fr ? 'Adresse' : 'Address' }}</dt>
          <dd>{{ legal.operatorAddress }}</dd>
        </template>
        <dt>Contact</dt>
        <dd>
          <a :href="`mailto:${legal.contactEmail}`">{{ legal.contactEmail }}</a>
        </dd>
        <template v-if="legal.publicationDirector">
          <dt>{{ fr ? 'Directeur de la publication' : 'Publication director' }}</dt>
          <dd>{{ legal.publicationDirector }}</dd>
        </template>
      </dl>
    </section>

    <section v-if="legal.hostName">
      <h2>{{ fr ? 'Hébergement' : 'Hosting' }}</h2>
      <dl>
        <dt>{{ fr ? 'Hébergé par' : 'Hosted by' }}</dt>
        <dd>{{ legal.hostName }}</dd>
        <template v-if="legal.hostAddress">
          <dt>{{ fr ? 'Adresse' : 'Address' }}</dt>
          <dd>{{ legal.hostAddress }}</dd>
        </template>
        <template v-if="legal.hostContact">
          <dt>Contact</dt>
          <dd>{{ legal.hostContact }}</dd>
        </template>
      </dl>
    </section>

    <section>
      <h2>{{ fr ? 'Le logiciel' : 'The software' }}</h2>
      <p v-if="fr">
        Ce serveur fait tourner Skillspector Web, un logiciel libre
        (<a
          :href="`https://github.com/${site.repo}`"
          target="_blank"
          rel="noopener"
        >code source</a>), qui analyse avec
        <a
          :href="`https://github.com/${site.scannerRepo}`"
          target="_blank"
          rel="noopener"
        >skillspector</a>. Il n’est ni affilié à NVIDIA ni approuvé par NVIDIA. Les noms et marques
        appartiennent à leurs titulaires.
      </p>
      <p v-else>
        This server runs Skillspector Web, open-source software
        (<a
          :href="`https://github.com/${site.repo}`"
          target="_blank"
          rel="noopener"
        >source code</a>), which scans with
        <a
          :href="`https://github.com/${site.scannerRepo}`"
          target="_blank"
          rel="noopener"
        >skillspector</a>. It isn’t affiliated with or endorsed by NVIDIA. Names and trademarks belong to
        their owners.
      </p>
    </section>

    <section>
      <h2>{{ fr ? 'Vos données' : 'Your data' }}</h2>
      <p v-if="fr">
        La <ULink :to="{ path: '/privacy', query: { lang: 'fr' } }">
          politique de confidentialité
        </ULink> indique ce que ce serveur conserve à votre sujet, pourquoi, combien de temps, et
        comment le faire supprimer.
      </p>
      <p v-else>
        The <ULink to="/privacy">
          privacy policy
        </ULink> says what this server keeps about you, why, for how long, and how to have it deleted.
      </p>
    </section>
  </LegalPage>
</template>
