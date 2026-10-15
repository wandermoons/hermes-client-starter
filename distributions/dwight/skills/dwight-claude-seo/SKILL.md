---
name: dwight-claude-seo
version: 1.0.0
description: "Primary client-safe SEO/GEO operating layer for Dwight, adapting AgriciDaniel/claude-seo v2.2.4 to Hermes for evidence-led audits, technical SEO, content, schema, GEO, SXO, clustering and reporting."
author: Wander Labs / Hermes adaptation of AgriciDaniel claude-seo
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [dwight, claude-seo, seo, geo, audit, technical-seo, schema, sxo, dataforseo]
---

# Dwight × Claude SEO — client-safe Hermes adapter

## Trigger and authority

Load this skill first for every Dwight task involving SEO, GEO, website audit, technical SEO, content quality, schema, sitemap, Core Web Vitals, AI-search visibility, SXO, semantic clustering, backlinks or SEO reporting.

Authority order:

1. Dwight's `SOUL.md`, security policy and approval rules.
2. The authorized client context in `local/CLIENT.md`, `local/onboarding.yaml` and any `client-*` skill.
3. This adapter's routing and evidence contract.
4. The vendored upstream methodology under `../claude-seo-upstream/`.

Never infer one client's domain, market, brand voice, credentials or permissions from another installation.

## Client context and locale

- Read `local/CLIENT.md` before any client-dependent analysis.
- Use the client's declared country and language. If they are still missing, state the assumption instead of silently choosing a market.
- A third-party domain may be inspected only when the user has authorized a public, read-only analysis. Never use that site's private data or mutate it.
- Scores are heuristics, never Google-internal metrics. Label estimates, sources, missing data and confidence.

## Runtime

Use only the profile-isolated commands installed by the starter:

```bash
./bin/dwight-claude-seo doctor --json
./bin/dwight-claude-seo setup
./bin/dwight-claude-seo run <script.py> [arguments]
./bin/dwight-schema-org-hook --url <URL> --mode always --evidence-dir <absolute-profile-artifacts-dir>
```

The runtime, browser, cache and configuration remain inside Dwight's profile. Never invoke upstream scripts with bare Python and never write into global Claude Code directories.

The upstream `/seo ...` notation is documentation, not a guaranteed Hermes slash command. Accept equivalent natural-language requests.

## Workflow — native Hermes orchestration

For full, standard or deep audits, load `dwight-claude-seo-fanout`. It translates the 18 upstream Claude Code agents into 18 bounded Hermes specialist skills and six dependency-ordered waves.

1. Parent Dwight collects and hashes deterministic evidence.
2. Parent runs the Schema.org gate for auditable HTML pages.
3. Parent delegates one orchestrator with explicit target, scope, locale, evidence directory, cost authorization and production prohibition.
4. The orchestrator dispatches sequential batches of at most three leaf specialists.
5. Leaves analyze immutable evidence only: no user contact, network acquisition, paid call, file write or production mutation.
6. Parent validates evidence IDs and writes the final client artifact.

If nested delegation is unavailable, run the applicable skills sequentially and disclose that the full fan-out was not exercised.

## Evidence hierarchy

1. Current first-party evidence explicitly authorized by the client.
2. Deterministic runtime outputs and public page evidence.
3. Paid external market/SERP data only with a current budget préautorisé and capped, or validation explicite for the exact call.
4. Current cited research, preferring primary sources.
5. Upstream heuristics, clearly labeled.

Never repeat dated numerical claims from a skill as current facts without checking their source.

## Safety and cost rules

- No paid API call without a current capped preauthorization or exact validation explicite.
- No publication, deletion, CMS mutation, indexing submission, credential change, outreach or permission change without exact validation explicite.
- A CMS draft is an external persistent mutation and also requires approval.
- Audit fan-out is read-only: leaf specialists must return `paid_calls: []` and `production_mutations: []`.
- Do not install optional extensions, enable hooks or change credentials merely because an upstream skill mentions them.
- Preserve upstream MIT attribution locally, but omit unrelated promotional footers from client deliverables.

## Client-ready output contract

For each major finding provide:

- evidence and source;
- impact;
- priority;
- recommended action;
- leading indicator;
- falsification test;
- confidence and limitations.

Finish with a short prioritized action plan. Never claim that an unavailable integration or failed runtime produced evidence.

## Verification

Before delivering an audit:

1. verify the target and authorization scope;
2. verify every evidence ID used in a major claim;
3. distinguish measured facts, inference and unavailable data;
4. confirm that no paid call or production mutation occurred without the applicable authorization;
5. preserve the evidence manifest and runtime diagnostics with the private client artifacts.
