<script setup lang="ts">
// Les conditions d'utilisation en français (app/pages/terms.vue) : les mêmes que TermsEn.vue, à
// garder en accord avec elles.
const { legal } = useLegal()
const { site } = useAppConfig()
</script>

<template>
  <section>
    <h2>Le service</h2>
    <p>
      Ce serveur, exploité par {{ legal.operatorName }}, vérifie les risques de sécurité des skills
      d’agents d’IA et des serveurs MCP avant que vous les installiez : il analyse ce que vous soumettez
      avec
      <a
        :href="`https://github.com/${site.scannerRepo}`"
        target="_blank"
        rel="noopener"
      >skillspector</a> et, si vous le demandez, le fait examiner par un modèle d’IA. Utiliser le
      service vaut acceptation de ces conditions. Le logiciel est libre, sous licence MIT ; ces
      conditions portent sur ce serveur.
    </p>
  </section>

  <section>
    <h2>Votre compte</h2>
    <ul>
      <li>Un compte est personnel. Indiquez une adresse e-mail à laquelle vous recevez du courrier.</li>
      <li>
        Gardez pour vous votre mot de passe, vos jetons d’API et vos clés : vous êtes responsable de ce
        qui en est fait. Révoquez un jeton ou changez votre mot de passe dès que vous pensez qu’il a
        fuité.
      </li>
      <li>Vous pouvez supprimer votre compte à tout moment, depuis votre page Compte.</li>
    </ul>
  </section>

  <section>
    <h2>Utilisation acceptable</h2>
    <p>
      Soumettre des skills suspects pour les faire vérifier est la raison d’être du service. S’en servir
      contre le service, ses prestataires ou quiconque ne l’est pas. En particulier, ne :
    </p>
    <ul>
      <li>soumettez pas de contenu auquel vous n’avez pas le droit d’accéder ou de faire analyser ;</li>
      <li>
        tentez pas de contourner les quotas, les limites de fréquence ou la protection contre les robots,
        par exemple avec plusieurs comptes, ni de surcharger le serveur ;
      </li>
      <li>
        tentez pas d’accéder aux données d’autres utilisateurs, aux secrets ou aux systèmes du serveur,
        ni d’utiliser les analyses pour atteindre d’autres systèmes que les hébergeurs de code prévus ;
      </li>
      <li>
        utilisez pas le service à des fins illicites, ni n’incluez sans raison de données personnelles
        ou de secrets d’autrui dans ce que vous soumettez.
      </li>
    </ul>
    <p>
      Vous avez trouvé une vulnérabilité ? Signalez-la en privé à
      <a :href="`mailto:${legal.contactEmail}`">{{ legal.contactEmail }}</a> plutôt que de l’exploiter.
    </p>
  </section>

  <section>
    <h2>Quotas</h2>
    <p>
      L’éditeur peut limiter le nombre d’analyses que chaque compte lance par jour et exécute en même
      temps, ainsi que la fréquence des requêtes. Votre page Compte indique vos limites actuelles. Elles
      peuvent changer, et les analyses peuvent être suspendues pour tous, par exemple lors d’un
      incident.
    </p>
  </section>

  <section>
    <h2>Les résultats sont un avis, pas une garantie</h2>
    <p>
      Les analyses sont automatiques, par analyse statique et, si vous l’activez, par un modèle d’IA.
      Elles peuvent manquer une menace réelle et signaler du code inoffensif. Un verdict « sûr » signifie
      que rien d’inquiétant n’a été trouvé, pas que le skill est sûr. Vous restez responsable de ce que
      vous installez et exécutez : lisez le code d’un skill, et jugez un résultat par vous-même, avant de
      lui faire confiance.
    </p>
  </section>

  <section>
    <h2>Ce que vous soumettez</h2>
    <ul>
      <li>
        Vous conservez tous vos droits sur ce que vous soumettez. Vous autorisez l’éditeur à le
        récupérer, le conserver et l’analyser, et à en montrer les résultats à vous et aux personnes
        avec qui vous les partagez, uniquement pour fournir le service.
      </li>
      <li>
        Avec l’analyse par IA, le contenu du skill est envoyé au fournisseur d’IA que vous avez choisi,
        selon ses propres conditions.
      </li>
      <li>
        Un résultat que vous partagez, ou ajoutez à un badge, est public : assurez-vous de pouvoir le
        publier, en particulier pour un dépôt privé.
      </li>
    </ul>
  </section>

  <section>
    <h2>Disponibilité</h2>
    <p>
      Le service est fourni en l’état, sans garantie de disponibilité. Une analyse peut échouer ou
      expirer. L’éditeur peut le modifier, le suspendre ou y mettre fin, et s’efforcera de prévenir
      avant une fermeture, pour que vous puissiez télécharger vos rapports.
    </p>
  </section>

  <section>
    <h2>Responsabilité</h2>
    <p>
      Dans les limites permises par la loi, l’éditeur n’est pas responsable des dommages indirects, ni
      des pertes dues à la confiance accordée à un résultat, à une analyse qui a échoué ou à
      l’indisponibilité du service. Rien dans ces conditions ne limite une responsabilité que la loi ne
      permet pas de limiter, ni les droits que la loi accorde aux consommateurs.
    </p>
  </section>

  <section>
    <h2>Suspension</h2>
    <p>
      L’éditeur peut suspendre ou supprimer un compte qui enfreint ces conditions, après en avoir
      indiqué la raison à son titulaire quand c’est possible, ou immédiatement en cas de manquement
      grave comme une attaque contre le service.
    </p>
  </section>

  <section>
    <h2>Modifications et droit applicable</h2>
    <p>
      Ces conditions évoluent avec le service ; la date en haut de page indique leur dernière mise à
      jour, et continuer à utiliser le service vaut acceptation.<template v-if="legal.governingLawFr || legal.governingLaw">
        Elles sont régies par {{ legal.governingLawFr || legal.governingLaw }}.
      </template> Questions :
      <a :href="`mailto:${legal.contactEmail}`">{{ legal.contactEmail }}</a>.
    </p>
  </section>
</template>
