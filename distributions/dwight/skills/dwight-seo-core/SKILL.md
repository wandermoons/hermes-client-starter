---
name: dwight-seo-core
description: "Workflow générique de Dwight pour stratégie SEO/GEO, recherche, rédaction, audit et opérations WordPress avec intégrations progressives."
version: 0.1.0
author: Wander Labs
license: Proprietary
metadata:
  hermes:
    tags: [seo, geo, content, wordpress, dataforseo, perplexity]
---

# Dwight SEO Core

Utilise ce skill pour toute stratégie SEO/GEO, recherche de mots-clés, plan éditorial, article, optimisation, audit ou opération WordPress.

## Préflight

1. Lire `local/CLIENT.md` et `local/onboarding.yaml` s’ils existent.
2. Identifier le domaine, l’audience, l’offre, la zone, la langue et l’objectif de conversion.
3. Vérifier quelles sources sont réellement accessibles.
4. Définir le livrable et les actions qui nécessitent une validation.

## Modes de fonctionnement

### Socle sans intégrations

Avec les informations du client et la recherche web disponible, tu peux produire : stratégie initiale, idées, clusters, briefs, articles et recommandations. Indique que les volumes, positions et performances ne sont pas mesurés.

### Perplexity disponible

Utilise Perplexity pour la recherche actuelle et les sources, pas comme modèle principal si le modèle ne prend pas en charge les outils. Vérifie un vrai appel avant de déclarer l’intégration prête.

### DataForSEO disponible

Utilise DataForSEO pour les données externes : SERP, volumes, concurrence, positions et backlinks. Garde Search Console comme source prioritaire pour les clics, impressions et requêtes du site appartenant au client.

### WordPress disponible

Teste dans cet ordre : racine REST publique, identité authentifiée, lecture de contenu, puis seulement une écriture explicitement autorisée. Utilise un utilisateur dédié et un Application Password.

## Workflow de contenu

1. Définir objectif, audience, intention et mot-clé principal.
2. Rechercher les faits et différencier données mesurées, sources externes et hypothèses.
3. Analyser le contenu existant et les risques de cannibalisation.
4. Construire H1, H2/H3, angle, preuves, exemples et conversion.
5. Rédiger dans la voix du client, sans remplissage SEO.
6. Préparer title, meta description, slug, FAQ, maillage et alt text.
7. Effectuer une relecture éditoriale et factuelle.
8. Soumettre à validation avant toute publication.

## Workflow d’audit

- Commencer par la question commerciale ou le symptôme observé.
- Comparer des périodes cohérentes lorsque les données le permettent.
- Séparer technique, contenu, intention, concurrence et saisonnalité.
- Ne pas attribuer une causalité sans preuve.
- Prioriser les actions par impact, confiance, effort et réversibilité.

## Vérification des écritures

Pour toute action autorisée :

1. enregistrer l’état précédent ;
2. appliquer la plus petite mutation possible ;
3. relire la ressource par l’API ;
4. vérifier le rendu public si nécessaire ;
5. conserver une preuve sans secret ;
6. signaler précisément tout échec ou résultat partiel.
