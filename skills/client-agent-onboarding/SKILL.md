---
name: client-agent-onboarding
description: "Accompagner un client dans la configuration progressive de son orchestrateur Hermes et du profil Dwight, sans exposer les secrets."
version: 0.1.0
author: Wander Labs
license: Proprietary
metadata:
  hermes:
    tags: [onboarding, profiles, dwight, client, security]
---

# Client Agent Onboarding

Utilise ce skill lorsqu’un client veut configurer, compléter, vérifier ou mettre à jour son environnement Hermes et le profil `dwight`.

## Sources locales

- Contexte métier : `$HERMES_HOME/local/CLIENT.md`
- État d’onboarding : `$HERMES_HOME/local/onboarding.yaml`
- Profil Dwight : `$HERMES_HOME/profiles/dwight/`
- Contexte Dwight : `$HERMES_HOME/profiles/dwight/local/CLIENT.md`

## Workflow

1. Lire l’état d’onboarding et résumer les capacités `ready`, `pending` et `blocked`.
2. Collecter les informations métier non sensibles avant les credentials.
3. Pour chaque intégration, expliquer l’accès minimal nécessaire et où le saisir sans le publier dans la conversation.
4. Écrire les credentials uniquement dans le stockage privé du profil Dwight ou utiliser le flux OAuth officiel.
5. Effectuer d’abord un test réel en lecture seule depuis le profil Dwight.
6. Redémarrer le gateway de Dwight si la configuration est chargée au démarrage.
7. Relancer un test depuis une nouvelle session Dwight.
8. Mettre à jour `onboarding.yaml` sans y inscrire de secret.
9. Demander une validation séparée avant le premier brouillon WordPress, puis avant la première publication.

## Règles d’intégration

- **WordPress** : utiliser un utilisateur dédié et un Application Password ; tester l’identité et la lecture avant toute écriture.
- **Google Search Console** : OAuth avec accès minimal ; vérifier la propriété ciblée.
- **DataForSEO** : vérifier le compte sans appel facturé lorsque c’est possible ; toute requête payante exige un budget préautorisé et plafonné ou une validation explicite couvrant endpoint, tâches, devise et coût maximal ; ne jamais inventer de volumes ou positions.
- **Perplexity** : tout appel Sonar potentiellement facturé exige un budget préautorisé et plafonné ou une validation explicite couvrant le modèle, le nombre d’appels et le coût maximal ; si la clé ou l’autorisation manque, utiliser la recherche web disponible et annoncer la limite.

## Gestion de profil

Toujours cibler explicitement Dwight :

```bash
hermes -p dwight config path
hermes -p dwight auth list
hermes -p dwight tools list
hermes -p dwight chat -q "Réponds uniquement : OK" --quiet
```

Ne jamais conclure qu’une intégration fonctionne sur la seule présence d’une variable. Un test réel est obligatoire.

## Sécurité

- Aucun secret dans GitHub, `CLIENT.md`, `onboarding.yaml`, les skills, la mémoire ou les logs de compte rendu.
- Aucune copie globale de `.env` entre profils.
- Aucune publication, suppression, permission ou dépense sans validation explicite.
- Une intégration non disponible reste `pending`; le mode dégradé doit être clairement annoncé.
