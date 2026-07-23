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

## Mise à jour

Depuis le même dossier :

```bash
git pull --ff-only
./install.sh
```

L’installateur vérifie la provenance du profil Dwight, met à jour la distribution, préserve les données locales, puis met à jour le profil orchestrateur.

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

## Statut

Version `0.1.1` — pilote. Le socle est volontairement générique ; les workflows avancés seront ajoutés après validation sur des environnements de test.

## Licence

Code visible publiquement, tous droits réservés à Wander Labs. Utilisation autorisée pour les installations et clients approuvés par Wander Labs.
