---
name: leo-flexible-sourcing
description: "Use when sourcing public businesses for a user-defined sector, zone, count, and Notion destination."
version: 0.1.0
author: Hermes Client Starter
license: Proprietary
metadata:
  hermes:
    tags: [sourcing, businesses, notion, deduplication, provenance]
    related_skills: [leo-notion-pipeline, leo-onboarding]
---

# Léo flexible sourcing

## Scope

Use this skill to discover and prepare public business candidates. It is intentionally independent of any fixed niche, geography, ideal-customer profile, provider, target database, data collector, campaign, or quota. Sourcing works without Instantly and never invokes it.

This skill discovers candidates through Hermes tools. The bundled Python helper only validates, normalizes, deduplicates, caps, and reports candidate data already supplied to it; it does not discover businesses.

## Required mission inputs

Do not start discovery until all four values are explicit:

- `sector`: the requested business category;
- `zone`: the requested geography or service area;
- `target_count`: a positive integer and hard output cap;
- `target_notion_database`: the target Notion database identifier or URL.

Accept optional inclusion criteria, exclusion criteria, desired evidence, languages, and ranking preferences. Do not manufacture defaults that narrow the market without telling the user.

## Workflow

### 1. Establish the destination and duplicate baseline

Load `leo-notion-pipeline`. Through the user's separate OAuth connection, verify the workspace and database identity read-only, inspect the current schema, and map its existing properties. Paginate the relevant existing rows before discovery and build the duplicate baseline from website/domain first, then normalized company name plus phone or email.

If Notion is not connected or the exact target cannot be verified, stop before discovery that is intended for writing. Explain the onboarding step; never substitute another database.

### 2. Discover with free tools first

Use free public URL routes first: web search, direct extraction of public pages, and browser inspection when rendering is required. Choose query wording from the supplied sector and zone rather than a hard-coded source or provider. Do not bypass logins, rate limits, access controls, anti-bot protections, or terms.

A paid tool is never an automatic fallback. Before any paid call, name the tool, purpose, maximum requests or results, and maximum cost. Proceed only after explicit capped approval for that exact use. Stop at the cap.

### 3. Verify every candidate

A candidate is eligible only when the evidence supports all of the following:

- a real business name;
- an official site that is reachable through an allowed public route;
- a target-zone relationship shown by an official contact page, location page, service-area statement, or another reliable public source;
- relevance to the supplied sector and optional criteria.

Do not treat a directory profile as the official site. Preserve its URL as discovery provenance, then verify the business on its official site. If the official site or zone cannot be verified, exclude the candidate with a reason rather than guessing.

For each retained candidate, keep:

- company name;
- canonical website and normalized domain;
- sector and zone evidence;
- any public professional phone or email that was actually observed;
- discovery source URLs and official-site evidence URLs;
- verification date and concise notes;
- unresolved fields explicitly marked unknown.

### 4. Normalize and deduplicate deterministically

Deduplicate against the complete Notion baseline and within the candidate batch:

1. canonical domain, ignoring scheme, `www`, path, query, fragment, case, and default port;
2. normalized company name plus normalized phone;
3. normalized company name plus normalized email.

Use `scripts/prepare_candidates.py` for a deterministic local pass when structured candidate JSON is available:

```bash
python3 scripts/prepare_candidates.py < mission-candidates.json
```

The input contains the four required mission fields, `candidates`, and `existing_records`. The helper performs no network I/O and no external writes. Its output is a preparation report, not proof that discovery or site verification occurred.

### 5. Preview and obtain mission approval

Present the proposed unique rows, exclusions, evidence gaps, duplicate reasons, destination identity, and maximum row count. Require explicit mission approval for the exact target database and proposed write scope before creating anything. Earlier permission to research is not permission to write.

This sourcing workflow must never contact a candidate, submit a form, import into outreach, activate a campaign, or send a message.

### 6. Write and verify through Notion

After approval, hand the exact approved set to `leo-notion-pipeline`. Write only mapped fields supported by the existing database. Then read back the exact created rows from the exact target and compare their identifiers, domains, names, provenance, and created count. A successful write response without readback is incomplete.

## Output report

Report mechanically:

- input candidates;
- verified eligible candidates;
- duplicates against Notion;
- duplicates within the batch;
- missing-site or unverified-zone exclusions;
- approved target count;
- rows proposed, rows created, and exact rows verified;
- paid calls and observed cost, or `none`;
- shortfall and reason, if any.

## Guardrails and verification

- [ ] Sector, zone, target_count, and target Notion database are explicit.
- [ ] Workspace/database identity and schema were checked read-only.
- [ ] Existing rows were paginated before writes.
- [ ] Every retained business has official site and zone evidence.
- [ ] Domains and fallback identity keys were normalized and deduplicated.
- [ ] Provenance is retained per candidate.
- [ ] Free tools were tried first.
- [ ] Every paid call had explicit capped approval.
- [ ] Mission approval covered the exact proposed write scope.
- [ ] Exact created rows were read back.
- [ ] No contact, import, activation, or send occurred.
