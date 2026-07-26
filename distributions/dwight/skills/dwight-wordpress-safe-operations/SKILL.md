---
name: dwight-wordpress-safe-operations
description: "Use whenever Dwight reads, drafts, updates, publishes, verifies or troubleshoots content on an authorized WordPress site."
version: 0.1.0
author: Wander Labs
license: Proprietary
metadata:
  hermes:
    tags: [dwight, wordpress, rest-api, publication, backup, verification]
---

# Dwight WordPress Safe Operations

Use this skill for every WordPress operation, including read-only inspection, draft creation, published edits, media, SEO metadata and publication.

## Default mode

- Read before writing.
- Local preparation is free, but **toute mutation** in WordPress requires **validation explicite** naming the site, object and action; this includes creation of a CMS draft.
- An approved draft creation must send `status=draft` explicitly. Never inherit a status from another object or prior request.
- Public, destructive, permission-changing or bulk actions require a separate precise approval when not already covered.
- Use a dedicated least-privilege account and application password.
- Credentials stay in the intended profile secret store.

## Preflight workflow

1. Read `local/CLIENT.md` and `local/onboarding.yaml`.
2. confirm exact site/domain and environment.
3. test the public REST root.
4. Require HTTPS for authenticated requests. Plain HTTP is allowed only for an explicitly authorized loopback/local test environment.
5. Disable or inspect redirections: never forward authentication to another origin or accept an HTTPS-to-HTTP downgrade.
6. verify authenticated identity and permissions without printing secrets.
7. resolve object type, ID, slug, language, status and canonical URL.
8. run duplicate guards before creating content.
9. define approved fields and fields that must remain unchanged.

## Read and draft workflow

Read-only inspection may gather current content, metadata, media, links and public rendering. After exact approval for new content:

1. create native Gutenberg blocks when block editing matters;
2. send `status=draft` explicitly unless publication is separately approved;
3. set only required fields;
4. read the draft back through the API with edit context;
5. verify ID, slug, status, raw block markers, language and media references.

A public draft URL returning 404 does not prove failure; authenticated API state is the source of truth for drafts.

## Published mutation workflow

After exact approval:

1. fetch the latest object with edit context;
2. create a timestamped **sauvegarde** of full JSON and raw content inside the client-private `local/` namespace with restrictive permissions;
3. capture public HTML when visual or conversion structure matters;
4. prepare the minimal field-level mutation;
5. compare headings, media, links, forms, reusable blocks and CTA before writing;
6. immediately before writing, fetch again and compare `ETag`, `modified` timestamp or a stable content hash with the prepared baseline; stop on divergence;
7. apply only approved fields;
8. relire la ressource via l’**API**;
9. for published content only, verify canonical and cache-busting **public** URLs; do not publicly probe a private draft;
10. verify title/meta, links, media, status and distinctive changed text;
11. preserve rollback evidence.

If any verification fails, report partial state precisely and do not repeat a create or publish call blindly.

## Media and multilingual guardrails

- Preserve existing media unless the task explicitly changes it.
- Keep provenance and human alt text for externally sourced images.
- Treat language assignment, translations, canonical and hreflang as separate concerns.
- Do not mutate multilingual relationships without a verified workflow.
- Avoid full-content replacement when a narrow text or link edit is sufficient.

## SEO metadata

Update only approved metadata. Verify the write response and API readback for every status; verify rendered public title/meta only for published content, and for a private draft use only authenticated preview/API data without any public probe. If plugin fields are not writable, return a manual-entry report instead of claiming success.

## Sécurité et guardrails

- Never request or expose a primary password in chat.
- Never send credentials over HTTP outside an explicitly authorized local test.
- Never forward authentication across an origin-changing redirection.
- Never publish, delete, unpublish, change roles, install plugins or run bulk edits without explicit approval.
- Never claim success from a request payload alone.
- Stop on domain, identity, object or language ambiguity.
- Keep backups and evidence free of secrets.

## Vérification

- [ ] Domain, identity, permissions and object are confirmed.
- [ ] Approval covers the exact mutation.
- [ ] Backup exists for every published edit.
- [ ] Only approved fields changed.
- [ ] API readback confirms persisted state.
- [ ] Public rendering and canonical URL were checked when applicable.
- [ ] Rollback path and any partial failure are documented.
