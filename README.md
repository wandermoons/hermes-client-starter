# Hermes Client Starter

Starter public pour déployer un environnement Hermes client composé de :

- un profil principal `default` configuré comme orchestrateur ;
- une distribution locale `dwight` spécialisée SEO/GEO, contenu, recherche et WordPress ;
- un onboarding progressif qui conserve les secrets et données client hors de GitHub.

## Installation

```bash
git clone https://github.com/wandermoons/hermes-client-starter.git
cd hermes-client-starter
./install.sh
```

Le script installe Dwight depuis `distributions/dwight/`. Aucun token GitHub, second clone ou accès à un dépôt privé n’est nécessaire.

## Capacités Dwight v0.1.2

Le Core comprend un routeur et huit capacités spécialisées :

- recherche actuelle et synthèse sourcée ;
- mots-clés, SERP, concurrents, rangs, backlinks et DataForSEO ;
- audit Google Search Console et priorisation des quick wins ;
- stratégie de silos et prévention de la cannibalisation ;
- briefs, rédaction SEO et QA éditoriale ;
- audit et correction sécurisée du maillage interne ;
- opérations WordPress en mode sûr ;
- extraction d’un Brand Voice Guide depuis un corpus détenu, licencié ou explicitement autorisé ; analyse descriptive non imitative pour les tiers publics.

Toutes les capacités distinguent données mesurées, sources externes et recommandations. Toute mutation externe persistante nécessite une validation explicite. Tout appel payant doit être couvert par un budget préautorisé et plafonné, sinon être validé précisément avant exécution.

## Mise à jour

Depuis le même dossier :

```bash
git pull --ff-only
./install.sh
```

L’installateur vérifie la provenance du profil Dwight, met à jour la distribution, préserve les données runtime et locales, puis met à jour le profil orchestrateur.

### Mise à jour sûre v0.1.2

Selon la version Hermes installée, `hermes profile update` peut remplacer le dossier `skills/` de la distribution en entier. Il faut donc utiliser `./install.sh`, pas la commande Hermes directe.

Avant l’update, l’installateur :

1. sauvegarde `SOUL.md`, `config.yaml`, `distribution.yaml` et tous les skills Dwight sous `local/migration-backups/` avec permissions restrictives ;
2. compare les fichiers Core installés au baseline de la version précédente ;
3. arrête sans écraser si un fichier Core a divergé ou si un nouveau nom Core entre en collision avec un skill local ;
4. restaure après update les dossiers de skills qui n’appartiennent pas à la distribution ;
5. restaure Dwight, sa configuration et l’onboarding canonique si une étape échoue, même après l’update Hermes.

L’installateur ne copie depuis le profil principal que les champs sûrs de sélection du modèle (`default`, `provider`, `base_url`). Il ne copie jamais les blocs providers, credentials, tokens ou stratégies d’authentification.

La personnalisation persistante et composable du SOUL reste le chantier v0.2.0. En v0.1.2, toute modification directe d’un fichier Core bloque volontairement la mise à jour.

## Données conservées localement

Les éléments suivants ne doivent jamais être ajoutés au dépôt :

- `.env` et `auth.json` ;
- clés API, tokens et mots de passe ;
- mémoires et sessions ;
- contexte et contenus d’un client ;
- sauvegardes WordPress et résultats d’API.

Le contexte canonique du client est créé dans le profil `default` sous `local/CLIENT.md`. Dwight y accède au moyen d’un lien local vérifié.

## Sécurité

- Déployer un conteneur ou une VM distinct par client.
- Les profils Hermes isolent leur état mais ne constituent pas une sandbox de sécurité.
- Les publications, suppressions, changements de permissions et dépenses exigent une validation explicite par défaut.
- Le script sauvegarde et restaure le `SOUL.md` et le skill d’onboarding du profil principal si une mutation échoue.
- Ne jamais contourner les contrôles d’accès, protections anti-bot ou conditions d’utilisation d’un site.

## Validation locale

```bash
bash -n install.sh
# Gate privé obligatoire : liste non committée, séparée par des virgules.
DWIGHT_PRIVATE_DENYLIST='<private-terms>' python3 -m unittest discover -s tests -v
bash tests/test_install_upgrade.sh
git diff HEAD --check
git diff --cached --check
# Sur un profil de test isolé déjà installé :
DWIGHT_TEST_PROFILE=<profil-test> bash tests/run_dwight_model_smoke.sh
```

Après installation isolée, exécuter un appel réel au modèle et les scénarios documentés dans `tests/test_dwight_core_prompts.md`.

## Statut

Version `0.1.2` — Dwight Core Capabilities. Déploiement pilote supervisé avant généralisation.

## Licence

Code visible publiquement, tous droits réservés à Wander Labs. Utilisation autorisée pour les installations et clients approuvés par Wander Labs.
