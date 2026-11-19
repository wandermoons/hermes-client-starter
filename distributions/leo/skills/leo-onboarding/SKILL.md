---
name: leo-onboarding
description: "Use to onboard Léo connections and collect a generic sourcing mission without storing credentials."
version: 0.1.0
author: Hermes Client Starter
license: Proprietary
metadata:
  hermes:
    tags: [onboarding, notion, instantly, sourcing, approvals]
    related_skills: [leo-flexible-sourcing, leo-notion-pipeline, leo-instantly-operations]
---

# Léo onboarding

## Goal

Prepare the profile for a user-defined sourcing mission while keeping integrations, credentials, and authorization boundaries explicit. The distribution ships with no credentials and no client-specific identifiers.

## Workflow

### 1. Collect the mission

Require:

- sector;
- zone;
- positive target count;
- target Notion database identifier or URL.

Record optional criteria only when the user supplies or approves them. Do not assume a niche, geography, ideal-customer profile, provider, database, collector, campaign, or quota.

### 2. Connect required Notion access

Guide the user through a separate OAuth connection for this profile. Never request a raw token in chat and never copy authorization from another profile. Once connected, load `leo-notion-pipeline` and perform only read-only checks until the user has verified:

- active workspace identity;
- exact existing database identity;
- current schema and proposed mapping.

Connection approval is not write approval. Keep the integration `pending` until identity checks pass, then mark it `ready_read_only`. A sourcing mission becomes `ready_to_preview` only after the duplicate baseline can be read.

### 3. Offer optional Instantly access

Explain that Instantly is optional and separate from Notion. Sourcing works without Instantly. If the user wants it, use a separate profile-local authorization supported by the chosen connector and verify workspace identity read-only through `leo-instantly-operations`.

Skipping or postponing Instantly does not degrade discovery, verification, deduplication, provenance, or Notion writes. No create, import, activation, or send permission is granted during connection.

### 4. Confirm approval and cost boundaries

Distinguish:

- approval to research public sources;
- explicit capped approval for a named paid tool;
- mission approval for the exact proposed Notion rows;
- separate approval for any optional external mutation.

No paid call may run without a named tool and an approved maximum cost, request count, or result count. Default to free tools first.

### 5. Readiness report

Report only non-secret state:

```text
Mission inputs: complete | missing
Notion OAuth: pending | connected
Notion identity: unverified | verified
Database identity: unverified | verified
Schema mapping: pending | ready
Duplicate baseline: pending | ready
Instantly connection: skipped | pending | connected
Instantly identity: unverified | verified
Paid-tool allowance: none | capped
Write approval: not requested | pending | approved
```

Do not store credentials, tokens, client records, or authorization artifacts in this distribution.

## Guardrails and verification

- [ ] All four mission inputs are explicit.
- [ ] Notion used separate OAuth and read-only identity checks.
- [ ] The existing database schema is mapped rather than replaced.
- [ ] Instantly is optional and uses a separate profile-local authorization if requested.
- [ ] Sourcing works without Instantly.
- [ ] Free tools are the default route.
- [ ] Paid use has explicit capped approval.
- [ ] Connection, research, write, import, activation, and send approvals remain separate.
- [ ] No credentials or fixed client identifiers were stored.
