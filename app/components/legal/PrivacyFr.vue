<script setup lang="ts">
// La politique de confidentialité en français (app/pages/privacy.vue) : la même que PrivacyEn.vue,
// à garder en accord avec elle. Ce qu'elle dit de ce serveur vient de ses réglages (useLegalFacts).
import type { LegalFacts } from '~/composables/useLegal'

defineProps<{ facts: LegalFacts }>()
const { legal } = useLegal()

const days = (count: number) => `${count} jour${count > 1 ? 's' : ''}`
</script>

<template>
  <section>
    <h2>Responsable du traitement</h2>
    <p>
      {{ legal.operatorName }} exploite ce serveur et est responsable des données personnelles qu’il
      traite. Pour toute question sur vos données, ou pour exercer vos droits, écrivez à
      <a :href="`mailto:${legal.contactEmail}`">{{ legal.contactEmail }}</a>.
    </p>
  </section>

  <section>
    <h2>Ce qui est conservé, et pourquoi</h2>
    <h3>Votre compte</h3>
    <ul>
      <li>
        Votre adresse e-mail, votre mot de passe (uniquement sous forme d’empreinte scrypt, dont on ne
        peut pas le retrouver), votre rôle, la date de création du compte et celle de votre dernière
        connexion. Ils sont nécessaires pour vous fournir un compte (exécution du contrat qui vous lie à
        l’éditeur).
      </li>
      <li>
        Votre session : un jeton aléatoire dans un cookie, <code>skillspector_session</code>, conservé
        {{ days(facts.sessionDays) }} ou jusqu’à votre déconnexion. Il est indispensable au
        fonctionnement du site, et ne demande donc pas votre consentement.<template v-if="facts.botProtection">
          Vercel BotID, qui protège le formulaire d’analyse contre les abus automatisés, dépose ses
          propres cookies de sécurité (nommés <code>KP_…</code>).
        </template> Il n’y a aucun cookie
        publicitaire ni de traçage.
      </li>
      <li>
        Si vous les créez : vos jetons d’API (leur nom et leur dernière utilisation ; le jeton lui-même
        uniquement sous forme d’empreinte), votre clé Claude (chiffrée en AES-256-GCM, utilisée
        uniquement pour vos propres analyses, et affichée seulement par ses derniers caractères), et
        votre connexion GitHub (votre nom d’utilisateur GitHub et ses jetons d’accès, chiffrés, utilisés
        seulement pour lire les dépôts que vous avez choisis, pour vos analyses).
      </li>
    </ul>
    <h3>Vos analyses</h3>
    <ul>
      <li>
        Ce que vous soumettez à l’analyse (un lien, le nom d’un skill dans un registre, ou un fichier),
        les options choisies, le rapport, le journal de l’analyse et le nombre de jetons d’IA utilisés.
        Ils sont nécessaires pour vous fournir le service. Vos analyses vous sont privées, sauf si vous
        les partagez.
      </li>
      <li>
        Un fichier envoyé est supprimé dès qu’il a été analysé, quel que soit le résultat ; seul son nom
        reste dans votre historique.
      </li>
      <li>
        Une clé collée pour une seule analyse, au lieu d’être enregistrée, n’est conservée que le temps
        de cette analyse{{ facts.hosted ? ', chiffrée, puis supprimée une fois l’analyse terminée' : '' }}.
      </li>
    </ul>
    <h3>Sécurité</h3>
    <ul>
      <li>
        Un journal d’activité des événements sur les comptes : inscriptions, changements et
        réinitialisations de mot de passe, ajout ou retrait de jetons d’API, de clés Claude et de
        connexions GitHub, partage de résultats ou ajout à un badge, et modifications faites par les
        administrateurs. Il est conservé {{ days(facts.activityDays) }}, pour enquêter sur un abus ou un
        incident de sécurité (intérêt légitime de l’éditeur à assurer la sécurité du service).
      </li>
      <li>
        Votre adresse IP, pour limiter la fréquence des connexions, des analyses et des consultations de
        pages partagées, ce qui empêche les abus.
        <template v-if="facts.hosted">
          Elle n’est conservée que pendant la durée de la limite concernée, 5 minutes au plus.
        </template>
        <template v-else>
          Elle n’est gardée que dans la mémoire de ce serveur, 5 minutes au plus.
        </template>
        L’hébergeur enregistre aussi les requêtes, avec leur adresse IP, dans ses propres journaux.
      </li>
      <li v-if="facts.botProtection">
        Quand vous lancez une analyse, Vercel BotID vérifie que la requête vient d’un navigateur et non
        d’un script automatisé.
      </li>
    </ul>
    <template v-if="facts.analytics || facts.speedInsights">
      <h3>Mesure d’audience</h3>
      <ul>
        <li v-if="facts.analytics">
          Vercel Web Analytics compte les visites sans cookie. Il reçoit le type de page visitée, jamais
          son adresse (qui peut contenir une analyse ou un lien partagé), et trois événements : la
          création d’un compte, le lancement d’une analyse (lien, fichier, dépôt GitHub ou serveur MCP,
          et si l’analyse par IA était activée) et la consultation d’un résultat (son verdict). Jamais ce
          qui a été analysé, votre e-mail ni aucun identifiant.
        </li>
        <li v-if="facts.speedInsights">
          Vercel Speed Insights mesure la vitesse de chargement des pages, avec les mêmes types de page.
        </li>
        <li>
          Cela permet à l’éditeur de voir comment le service est utilisé et de l’améliorer (intérêt
          légitime).
        </li>
      </ul>
    </template>
    <h3>Dans votre navigateur</h3>
    <p>
      Le formulaire d’analyse retient vos derniers choix (la source, l’analyse par IA, le fournisseur
      et le modèle, jamais une clé), et le site retient votre thème clair ou sombre, dans le stockage
      local de votre navigateur. Ces informations ne le quittent pas.
    </p>
  </section>

  <section>
    <h2>Ce qui est public</h2>
    <p>
      Rien, sauf si vous le décidez. Un résultat que vous partagez peut être ouvert par toute personne
      qui a son lien, qui montre le rapport mais pas qui a lancé l’analyse, jusqu’à ce que vous le
      révoquiez. Un résultat ajouté à un badge d’état montre son verdict à quiconque voit le badge.
    </p>
  </section>

  <section>
    <h2>Qui d’autre y a accès</h2>
    <ul>
      <li v-if="legal.hostName">
        {{ legal.hostName }}, qui héberge le serveur{{ facts.hosted ? ', conserve les fichiers envoyés jusqu’à leur analyse, et exécute chaque analyse dans un bac à sable isolé' : '' }}.
      </li>
      <li v-if="legal.databaseProvider">
        {{ legal.databaseProvider }}, qui héberge la base de données.
      </li>
      <li v-if="legal.emailProvider">
        {{ legal.emailProvider }}, qui envoie les e-mails de réinitialisation de mot de passe.
      </li>
      <li>
        Le fournisseur d’IA que vous choisissez, seulement quand vous activez l’analyse par IA : il
        reçoit le contenu du skill analysé{{ facts.hosted ? ' (Anthropic, avec votre propre clé)' : '' }}, selon ses propres conditions.
      </li>
      <li>
        GitHub, si vous connectez votre compte, pour lire les dépôts que vous avez choisis. Les
        hébergeurs de code des liens analysés voient le serveur les récupérer, pas vous.
      </li>
      <li>
        Les administrateurs de ce serveur, qui voient les adresses e-mail et les noms des jetons d’API
        des comptes, les analyses (pas le contenu d’une analyse d’un dépôt privé) et le journal
        d’activité, pour faire fonctionner le service.
      </li>
    </ul>
    <p>
      Vos données ne sont jamais vendues, ni utilisées à des fins publicitaires. Certains de ces
      prestataires sont établis aux États-Unis ou y traitent des données ; ces transferts reposent sur
      les garanties prévues par le RGPD, comme le cadre de protection des données UE–États-Unis ou les
      clauses contractuelles types de la Commission européenne.
    </p>
  </section>

  <section>
    <h2>Durées de conservation</h2>
    <ul>
      <li>
        Votre compte, ses clés, jetons et connexions : jusqu’à ce que vous le supprimiez, ou qu’un
        administrateur le fasse.
      </li>
      <li>
        Vos analyses :
        <template v-if="facts.scanDays !== null">
          {{ days(facts.scanDays) }}, ou moins si vous les supprimez, ou supprimez votre compte, avant.
        </template>
        <template v-else>
          jusqu’à ce que vous les supprimiez, ou supprimiez votre compte.
        </template>
      </li>
      <li>Les sessions : {{ days(facts.sessionDays) }}, ou jusqu’à votre déconnexion.</li>
      <li>Les liens de réinitialisation de mot de passe : 24 heures, ou jusqu’à leur utilisation.</li>
      <li>Le journal d’activité : {{ days(facts.activityDays) }}.</li>
      <li>
        Les fichiers envoyés : jusqu’à leur analyse, en général quelques minutes ; 7 heures au plus si
        l’analyse n’a jamais lieu.
      </li>
      <li>Les adresses IP pour les limites de fréquence : 5 minutes au plus.</li>
    </ul>
    <p v-if="facts.hosted">
      Les sauvegardes de la base de données faites par les hébergeurs peuvent contenir des données
      supprimées un peu plus longtemps, jusqu’à leur expiration.
    </p>
  </section>

  <section>
    <h2>Vos droits</h2>
    <p>
      Conformément au RGPD, vous pouvez accéder à vos données, les faire rectifier ou effacer, en
      limiter le traitement ou vous y opposer, et les recevoir dans un format portable.
    </p>
    <ul>
      <li>
        <strong>Supprimez votre compte</strong> vous-même, depuis votre page Compte : vos analyses et
        leurs rapports, vos liens partagés et badges, vos clés, jetons et connexions sont supprimés
        immédiatement, et le journal d’activité garde ses entrées sans votre e-mail.
      </li>
      <li>Supprimez une analyse depuis sa page de résultat, et téléchargez-y tout rapport.</li>
      <li>
        Pour toute autre demande, écrivez à
        <a :href="`mailto:${legal.contactEmail}`">{{ legal.contactEmail }}</a>. Vous recevrez une
        réponse dans un délai d’un mois.
      </li>
    </ul>
    <p>
      Si vous estimez que vos données ne sont pas traitées correctement, vous pouvez introduire une
      réclamation auprès de
      {{ legal.supervisoryAuthorityFr || legal.supervisoryAuthority || 'l’autorité de protection des données de votre pays de résidence' }}.
    </p>
  </section>

  <section>
    <h2>Sécurité des données</h2>
    <p>
      Les mots de passe sont hachés, les clés et jetons chiffrés ou hachés, les échanges passent par
      HTTPS, et le cookie de session ne peut pas être lu par les scripts de la page.<template v-if="facts.hosted">
        Les analyses s’exécutent dans un bac à sable qui ne détient aucun secret du serveur.
      </template>
    </p>
  </section>

  <section>
    <h2>Modifications</h2>
    <p>
      Cette politique évolue avec le service. La date en haut de page indique sa dernière mise à jour.
    </p>
  </section>
</template>
