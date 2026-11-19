---
name: leo-instantly-operations
description: "Use for optional, separately approved Instantly onboarding and lead or campaign operations."
version: 0.1.0
author: Hermes Client Starter
license: Proprietary
metadata:
  hermes:
    tags: [instantly, oauth, onboarding, approvals, readback]
    related_skills: [leo-onboarding, leo-flexible-sourcing]
---

# Léo optional Instantly operations

## Scope

Instantly is optional. It is not used for discovery, official-site verification, Notion deduplication, or normal sourcing. Sourcing must remain fully usable when Instantly is absent, disconnected, or intentionally skipped.

This distribution contains instructions only and no credentials, workspace IDs, list IDs, campaign IDs, contacts, or historical activity.

## Separate profile-local onboarding

The user connects Instantly through the authorization method supported by the chosen connector, such as OAuth or an API credential entered locally in the secure setup flow. Do not copy another profile's authorization and do not request a secret in chat. Once connected, read-only checks are allowed to verify the active workspace identity and inspect named objects the user asks about.

Report identity uncertainty and stop before any mutation. A successful connection does not authorize creating, importing, activating, or sending.

## Authorization boundaries

Each of these is a distinct external mutation and requires explicit approval for an exact target and scope:

- create a list, campaign, or other object;
- import or associate a frozen lead cohort;
- update lead or personalization data;
- alter sequence, schedule, sender, tracking, limits, or status;
- activate, pause, resume, launch, or send.

Approval for one action never implies another. In particular, import approval is not activation or send approval. Never infer permission from an active campaign because newly associated leads may become send-eligible.

The sourcing skill never contacts or sends and must not call this skill automatically. Any outreach operation is a separate user-requested mission.

## Read-only preflight

Before a proposed operation:

1. verify workspace identity read-only;
2. fetch the exact destination by user-supplied name or identifier;
3. inspect current status and settings that could cause automatic sending;
4. freeze the exact cohort and deduplicate by normalized email and domain;
5. validate every personalization value used by the destination;
6. preview the action, counts, exclusions, and side effects.

Unknown personalization values remain blank; never derive a company name or contact detail from an unverified page title or pattern.

## Mutation and readback

After explicit approval, set fields and safety options explicitly. For asynchronous jobs, wait for terminal status. Then read back the exact created, imported, updated, or activated objects and compare the exact identifiers, email set, personalization fields, status, and count.

Sending requires explicit approval that names the exact cohort, destination, and sending scope. After an approved send, read back provider evidence for the exact operation; never report a send from a queued request alone.

Do not retry a failed mutation automatically. Report partial results and request a decision.

## Guardrails and verification

- [ ] Instantly was optional and separately requested.
- [ ] Connection used a separate profile-local authorization; no credentials are in the distribution.
- [ ] Workspace and destination identity were verified read-only.
- [ ] The exact cohort and side effects were previewed.
- [ ] Explicit approval covered this exact create, import, update, activate, or send action.
- [ ] No broader settings were changed.
- [ ] Exact affected records and status were read back.
- [ ] Sourcing remains independent of Instantly.
