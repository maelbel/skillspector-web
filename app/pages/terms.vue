<template>
  <LegalPage
    v-slot="{ fr }"
    title="Terms of use"
    lead="The rules for using this server, and what its results can and can’t tell you."
    title-fr="Conditions d’utilisation"
    lead-fr="Les règles d’utilisation de ce serveur, et ce que ses résultats peuvent ou non vous apprendre."
  >
    <LegalTermsFr v-if="fr" />
    <LegalTermsEn v-else />
  </LegalPage>
</template>
