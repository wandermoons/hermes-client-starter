---
name: dwight-seo-internal-linking
description: "Use when Dwight audits, designs or safely corrects internal links between pillars, satellites, service pages and supporting content."
version: 0.1.0
author: Wander Labs
license: Proprietary
metadata:
  hermes:
    tags: [dwight, seo, internal-linking, silo, audit, wordpress]
---

# Dwight SEO Internal Linking

Use this skill for internal-link audits, silo matrices and approved link corrections.

## Principles

1. Audit before editing.
2. Use the live CMS/API and rendered HTML as source of truth.
3. Distinguish contextual body links from menus, breadcrumbs, related-post widgets and previous/next navigation.
4. Link only to valid canonical URLs.
5. Prefer helpful editorial context over keyword-stuffed anchors.
6. Keep link-only changes narrow.

## Audit workflow

1. Define every URL's role: pillar, satellite, service, conversion or supporting page.
2. Confirm status, canonical URL, language and HTTP availability.
3. Fetch source/raw content when authorized.
4. If the source is published, fetch rendered public HTML; for a draft/private source, use only authenticated API or private preview data and never probe it publicly.
5. Extract body links separately from global/theme links.
6. Build a source → target matrix.
7. Check required relationships:
   - every published satellite links to its pillar;
   - the pillar links to relevant published satellites;
   - draft or planned URLs are not linked publicly;
   - adjacent topics cross-link only when useful;
   - conversion links remain intact.
8. Report missing, broken, redirected, duplicate and non-contextual links.
9. Propose exact source section, destination and natural anchor context.

## Correction workflow

Only after validation explicite for the exact site and objects:

1. fetch current editable content;
2. save a full sauvegarde and raw-content copy;
3. prepare the smallest possible delta;
4. assert the target link is not already present;
5. preserve headings, media, forms, CTA and unrelated links;
6. apply the approved change;
7. read back through the API;
8. if the source is published, verify the rendered public page and target HTTP status; for a draft/private source, use authenticated API or preview verification and never probe it publicly;
9. rebuild the matrix and confirm the intended delta only.

Make correction scripts idempotent: an already-correct link must be skipped, not duplicated.

## Output format

```markdown
## État
- Correct
- Manquant
- Cassé ou redirigé
- Présent seulement dans la navigation

## Corrections proposées
| Source | Section | Destination | Contexte d’ancre |

## Vérification
- Matrice avant/après et statuts HTTP
```

## Sécurité et guardrails

- No public edit without exact approval.
- Never count navigation links as equivalent to contextual body links.
- Do not alter images, layout, forms, CTA or publication status during a link-only task.
- Stop if current content differs materially from the version used to prepare the change.
- Never print CMS credentials.

## Vérification

- [ ] Source and target canonical URLs are confirmed.
- [ ] Raw/body and rendered links were both checked.
- [ ] Published and draft states are distinguished.
- [ ] Backup exists before any write.
- [ ] API readback confirms the change; public rendering is checked only for published content.
- [ ] The final matrix contains no duplicate or dead approved links.
