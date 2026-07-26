---
name: dwight-seo-silo-strategy
description: "Use when Dwight turns a business topic into a keyword cluster, pillar/satellite architecture, editorial roadmap or anti-cannibalization decision."
version: 0.1.0
author: Wander Labs
license: Proprietary
metadata:
  hermes:
    tags: [dwight, seo, silo, clustering, cannibalization, content-strategy]
---

# Dwight SEO Silo Strategy

Use this skill to design a coherent topic architecture, not merely a list of keywords.

## Core rule: inventory first

Before external expansion, inspect:

- live sitemap and canonical URLs;
- existing pages, posts and language variants;
- current drafts, briefs or client notes when authorized;
- Search Console signals when available;
- existing internal-link structure.

Classify existing coverage as `keep`, `optimize`, `merge`, `link`, `exclude` or `create`. Never label an existing intent as new without verification.

## Silo workflow

1. Define audience, offer, conversion objective, market and language.
2. Build an exclusion map from existing content.
3. Generate a small seed set from genuine business problems.
4. Collect first-party signals and external keyword/SERP evidence.
5. Cluster by intent and expected page type, not lexical similarity alone.
6. Compare SERP URL overlap:
   - strong overlap often supports one comprehensive page;
   - distinct results and user needs may justify separate pages.
7. Select the pillar:
   - broad enough to organize the topic;
   - commercially or strategically meaningful;
   - supported by credible expertise and proof.
8. Select satellites with distinct jobs and no doorway-page pattern.
9. Define pillar ↔ satellite links and useful cross-links.
10. Sequence briefs, production, publication and measurement.

## Cannibalization checks

For every proposed page, record:

- primary intent;
- target reader and funnel stage;
- existing nearest URL;
- overlap risk;
- unique evidence, angle or format;
- recommended action: create, optimize, merge or postpone.

Do not split pages only to target minor keyword variants. Do not combine clearly different intents simply to make one long article.

## Recommended output

```markdown
## Décision
Pillar proposé ou page existante à renforcer.

| Priorité | Cluster | Intention | Type | Statut | Justification |
|---:|---|---|---|---|---|

## Architecture
- Pilier
- Satellites
- Maillage

## Risques
- Cannibalisation, manque de preuve ou dépendance à valider

## Prochaine étape
Le prochain brief à produire.
```

## Sécurité et guardrails

- No invented search volume or performance data.
- No paid keyword expansion without required approval.
- No creation or publication in a CMS without explicit validation.
- Do not expose private client strategy or mix data across clients.
- Favor a small defensible architecture over dozens of thin pages.

## Vérification

- [ ] Live content was inventoried first.
- [ ] Clusters are based on intent.
- [ ] Every new page has a distinct role.
- [ ] Pillar and satellite linking is defined.
- [ ] Evidence quality and uncertainty are visible.
- [ ] One next action is explicit.
