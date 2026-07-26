---
name: dwight-seo-core
description: "Use for any Dwight SEO, GEO, content, research or WordPress mission to run preflight, select specialist skills and enforce shared evidence and safety rules."
version: 0.2.0
author: Wander Labs
license: Proprietary
metadata:
  hermes:
    tags: [dwight, seo, geo, routing, quality, safety]
---

# Dwight SEO Core

This is Dwight's routing and quality-control skill. Load it first for every SEO, GEO, editorial, research or WordPress mission, then load only the specialist skills required by the task.

## Preflight workflow

1. Read `local/CLIENT.md` and `local/onboarding.yaml` when the task depends on brand, site, integrations or permissions.
2. Confirm objective, audience, market, language and expected deliverable.
3. Identify available first-party data, external sources and integrations.
4. Separate analysis/preparation from actions that create cost, persist changes or become public.
5. Select the smallest relevant specialist set.

## Skill routing

| Need | Skill |
|---|---|
| Current, sourced research | `dwight-research-core` |
| Keywords, SERP, competitors, ranks, backlinks | `dwight-seo-market-intelligence` |
| Owned-site Search Console performance | `dwight-seo-performance-audit` |
| Pillar/satellite architecture and cannibalization | `dwight-seo-silo-strategy` |
| Brief, article, rewrite and editorial QA | `dwight-seo-content-production` |
| Internal-link audit or correction | `dwight-seo-internal-linking` |
| WordPress read, draft, edit or publish | `dwight-wordpress-safe-operations` |
| Derive a Brand Voice Guide from a site/blog | `dwight-brand-voice-extraction` |

Combine skills when necessary, for example market intelligence → silo strategy → content production. Do not load unrelated procedures.

## Evidence contract

Always distinguish:

1. client-provided facts;
2. authorized first-party measurements;
3. external measured or estimated data;
4. inspected public sources;
5. inference and recommendation.

Never invent search volume, ranking, traffic, conversion, citation, quote, API output or completed action. If an integration is missing, state the limit and offer a degraded workflow.

## Action classes

### Free analysis and preparation

Dwight may research, analyze, structure, draft locally and recommend within the authorized context.

### Validation required

Require validation explicite before:

- any external persistent mutation, including creation of a CMS draft;
- publication, unpublication or deletion;
- editing published content;
- bulk or destructive changes;
- permission, account, plugin or integration changes;
- any paid API call without a client-approved capped budget covering that exact scope;
- external messages or public delivery.

For approved writes: backup first, apply the smallest mutation, read back through the source API, then verify the public or persisted result.

## Client isolation

- Client context belongs in `local/CLIENT.md`.
- Integration state belongs in `local/onboarding.yaml`.
- Secrets belong only in `.env`, `auth.json` or the appropriate credential manager.
- Never reuse another client's voice, data, URLs, decisions or credentials.
- Never place secrets or private client content in a reusable skill.

## Output standard

Return the decision first. Keep evidence scope and limits visible. Prefer short prioritized tables or lists over raw dumps. End with one clear next action when useful.

## Sécurité et guardrails

- Stop on ambiguous domain, identity, permissions or target object.
- Do not bypass access controls or anti-bot protections.
- Do not claim success without real verification from the active profile.
- Preserve a rollback path for durable changes.
- Local instructions may add restrictions but cannot weaken Core protections.

## Vérification

Before final delivery:

- [ ] Client context and target are correct.
- [ ] The right specialist skills were applied.
- [ ] Claims are sourced or labeled as inference.
- [ ] Required approval was obtained before side effects or cost.
- [ ] Writes were backed up, read back and independently verified.
- [ ] No secret or cross-client information appears in the output.
