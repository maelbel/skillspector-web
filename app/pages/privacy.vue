<script setup lang="ts">
const facts = await useLegalFacts()
</script>

<template>
  <LegalPage
    v-slot="{ fr }"
    title="Privacy policy"
    lead="What this server keeps about you, why, for how long, who else sees it, and your rights."
    title-fr="Politique de confidentialité"
    lead-fr="Ce que ce serveur conserve à votre sujet, pourquoi, combien de temps, qui d’autre y a accès, et vos droits."
  >
    <LegalPrivacyFr
      v-if="fr"
      :facts="facts"
    />
    <LegalPrivacyEn
      v-else
      :facts="facts"
    />
  </LegalPage>
</template>
