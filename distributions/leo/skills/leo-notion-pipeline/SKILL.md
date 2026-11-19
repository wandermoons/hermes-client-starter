---
name: leo-notion-pipeline
description: "Use when onboarding or operating an adaptable user-provided Notion sourcing database."
version: 0.1.0
author: Hermes Client Starter
license: Proprietary
metadata:
  hermes:
    tags: [notion, oauth, onboarding, pipeline, readback]
    related_skills: [leo-flexible-sourcing, leo-onboarding]
---

# Léo Notion pipeline

## Scope

Notion is the required destination for an approved sourcing mission. The user supplies an existing database identifier or URL. This distribution contains instructions only: no credentials, OAuth grants, workspace identifiers, database identifiers, or schema-specific values.

## Separate OAuth onboarding

The user connects Notion through a separate OAuth flow for this profile. Never copy another profile's OAuth data and never ask for an access token in chat or place one in a file under the distribution.

After connection and before writes:

1. run the available read-only identity check;
2. verify the expected workspace identity with the user;
3. fetch the exact target database read-only from the supplied identifier or URL;
4. report its title, stable identifier, parent/workspace context, and accessible property names;
5. stop if the workspace or database identity is ambiguous or unexpected.

A configured integration is not proof of the correct target. The workspace and database identity must be verified read-only in the active profile.

## Adapt to the existing database

Do not require a new fixed database or fixed schema. Inspect the existing database and create a mission-local mapping from logical fields to compatible user properties. Typical logical fields are company name, website, domain, sector, zone, phone, email, sources, verification notes, and verification date, but only mapped properties may be written.

- Reuse compatible existing properties.
- Explain missing or incompatible fields.
- Preserve provenance in a mapped text/URL field or page body when the existing schema supports it.
- Do not create a database, add properties, rename properties, or change property types during sourcing.
- Any schema mutation is a separate operation requiring explicit approval and readback; it is never implied by mission approval.

## Read-only duplicate baseline

Before proposing writes, paginate the relevant existing rows to exhaustion. Normalize and compare in this order:

1. domain derived from website;
2. normalized company name plus normalized phone;
3. normalized company name plus normalized email.

Treat archived, suppressed, or do-not-contact records as duplicates when present. Do not overwrite an existing row merely because some fields are blank.

## Approved writes

Before creating rows, show:

- verified workspace and database identity;
- schema mapping;
- exact proposed row count and candidate keys;
- skipped duplicates and unmapped fields;
- the fact that sourcing does not contact or send.

Require explicit mission approval naming or unambiguously referring to this target and scope. Set every mapped field explicitly. Do not rely on provider defaults for status, owner, campaign, or communication fields.

## Mandatory readback

After a create operation:

1. capture the returned row/page identifiers;
2. fetch each exact created row from the target database;
3. compare company, canonical domain, mapped provenance, and other approved fields;
4. verify the exact created count mechanically;
5. report mismatches without retrying a write automatically.

A provider success response is not completion. Exact read back from the target is required before reporting success.

## Guardrails and verification

- [ ] Connection used separate OAuth and contains no credentials in the distribution.
- [ ] Workspace and database identity were verified read-only.
- [ ] The mapping adapted to the existing database.
- [ ] Existing rows were paginated and deduplicated before writes.
- [ ] Mission approval covered the exact target and row set.
- [ ] No unapproved schema mutation occurred.
- [ ] Every created row was read back and compared.
- [ ] No contact or send occurred.
