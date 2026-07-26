---
name: dwight-seo-performance-audit
description: "Use when Dwight audits an authorized site's SEO performance from Search Console, analytics, sitemaps and live pages to identify measurable priorities."
version: 0.1.0
author: Wander Labs
license: Proprietary
metadata:
  hermes:
    tags: [dwight, seo, audit, search-console, performance, quick-wins]
---

# Dwight SEO Performance Audit

Use this skill when the question starts from an owned site's actual performance rather than generic keyword ideation.

## Goal

Turn measured data into a short decision list:

- pages to optimize;
- titles/metas to improve;
- content to refresh, merge or create;
- internal links to add;
- technical or indexing issues to investigate;
- topics to ignore for now.

## Preflight

1. Read `local/CLIENT.md` and `local/onboarding.yaml`.
2. Confirm the authorized property and business objective.
3. Verify the integration with a real API call before claiming it works.
4. Select coherent periods; default to 28 days for freshness and 90 days for stability.
5. Record filters, dimensions, timezone and comparison windows.

## Audit workflow

1. Pull property totals without dimensions when totals matter.
2. Pull top pages, top queries and query-page combinations.
3. Add country/device filters only when they answer the business question.
4. Inventory the sitemap and live URLs.
5. Inspect current title, meta, H1, status and content of shortlisted pages.
6. Compare with prior periods only when seasonality and update dates make the comparison meaningful.
7. Classify each signal:
   - CTR quick win;
   - striking-distance page;
   - content refresh;
   - new distinct intent;
   - internal-link opportunity;
   - technical/indexing issue;
   - postpone.
8. Rank by impact, confidence, effort, reversibility and business fit.

## Interpretation rules

- Query-dimension rows may omit anonymized queries; do not sum them as an exhaustive page total.
- Average position is aggregated, not a precise rank check.
- Correlation after a content update is not proof of causality.
- Very recent changes may not have stable Search Console data yet.
- A public HTML inspection is not a Search Console audit.
- Do not recommend a new page until sitemap and live content confirm the intent is not already covered.

## Output format

```markdown
## Synthèse
- Opportunité principale
- Quick win
- Risque ou limite

## Actions
| Priorité | Signal mesuré | Action | Impact | Confiance |

## Prochaine action
Une seule étape recommandée.
```

## Sécurité et guardrails

- Use only properties the client has authorized.
- Never expose OAuth files, tokens or private exports.
- Never invent clicks, impressions, CTR, position or conversion.
- Analysis is allowed; writes to the site or Search Console require separate validation.
- Store raw evidence locally without secrets and avoid publishing it by default.

## Vérification

- [ ] API access and property identity were tested.
- [ ] Periods, filters and dimensions are stated.
- [ ] Totals and query detail are not conflated.
- [ ] Existing live content was checked.
- [ ] Recommendations are measurable and prioritized.
- [ ] Missing data and attribution limits are explicit.
