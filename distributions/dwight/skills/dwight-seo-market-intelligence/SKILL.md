---
name: dwight-seo-market-intelligence
description: "Use when Dwight researches keywords, live SERPs, competitors, rankings, backlinks or market demand with web research, DataForSEO and other external SEO sources."
version: 0.1.0
author: Wander Labs
license: Proprietary
metadata:
  hermes:
    tags: [dwight, seo, serp, dataforseo, competitors, keywords]
---

# Dwight SEO Market Intelligence

Use this skill for external SEO questions: what people search, what ranks now, which competitors dominate, how a domain ranks in a precise market, and which external links may matter.

## Data boundary

- **Google Search Console**: first-party clicks, impressions, CTR, average position, pages and queries for an authorized owned property.
- **DataForSEO or equivalent**: external keyword estimates, current SERPs, competitors, precise location/device rank checks and backlink intelligence.
- **Web research**: source and intent analysis when paid data is unavailable.

Never present third-party estimates as exact Google truth. Never use external tools to fabricate owned-site performance.

## Preflight

1. Read `local/CLIENT.md` and `local/onboarding.yaml` when available.
2. Confirm domain, market, language, location, device and business objective.
3. Inventory existing site content before proposing new topics.
4. Classify the request as first-party, external or mixed.
5. Identify available tools and expected cost.

## Market intelligence workflow

### Keyword opportunities

1. Start from 1–5 business-relevant seeds.
2. Exclude already-covered intents and obvious noise.
3. Gather variants and estimates from available sources.
4. Validate the strongest terms against live SERP shape.
5. Cluster by search intent, not wording alone.
6. Prioritize business fit, intent, evidence, feasibility and differentiation.
7. Return a shortlist, never an unfiltered keyword dump.

### SERP and competitor analysis

1. Fix country, language, city when relevant, device and depth.
2. Inspect the top organic results and SERP features.
3. Separate true competitors from directories, media, marketplaces and platforms.
4. Compare page type, angle, title/H1, topical coverage, proof and authority signals.
5. Recommend create, optimize, merge, link, earn citations or postpone.

### Precise rank check

Report exact keyword, location, language, device, timestamp, checked depth, observed position and ranking URL. If absent, say `not found in top N`, never `not ranking`.

## Cost discipline

A paid call is allowed only when either:

- `local/` records a current **budget préautorisé**, with covered endpoints, period, devise and hard cap; or
- the client gives a validation explicite for the proposed call.

Before requesting approval, state:

- endpoint/category;
- keyword and task count;
- location, language, device and depth;
- devise and **coût maximal**;
- why free, internal or Google Search Console data is insufficient;
- proposed reduced first pass.

Without a matching capped budget, require approval before every paid call. Prefer small batches and lower-cost queue modes when time allows.

After a timeout or ambiguous POST failure, **ne re-POSTe jamais** la task blindly: it may already exist and be billed. Reconcile it using the returned or client-side **identifiant de tâche**; retry only idempotent reads or a POST proven not to have created a task.

## Output format

```markdown
## Décision
...

## Périmètre des données
- Source, marché, langue, appareil, date

## Opportunités prioritaires
| Priorité | Requête/cluster | Intention | Preuve | Action |

## Limites
- Estimations tierces, profondeur ou données manquantes
```

## Sécurité et guardrails

- Credentials remain in the intended profile secret store.
- Minimize payloads sent to external providers; do not send private drafts, personal data or raw first-party query exports unless the client explicitly authorizes that transfer.
- No paid call outside a matching preauthorized capped budget or exact approval.
- No publication or site mutation based solely on market data.
- No invented volume, difficulty, backlink, ranking or API success.
- Never duplicate a potentially billed task after an ambiguous failure.

## Vérification

- [ ] Existing content was checked before recommending creation.
- [ ] Google Search Console and DataForSEO roles are clearly separated.
- [ ] Scope, location, language, device and date are reported.
- [ ] Estimates are labeled as estimates.
- [ ] Recommendations are short, prioritized and tied to business value.
