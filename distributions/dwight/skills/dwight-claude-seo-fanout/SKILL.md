---
name: dwight-claude-seo-fanout
description: 'Orchestrate Dwight Claude SEO audits through a two-level Hermes fan-out/fan-in: one orchestrator child and six
  sequential batches of up to three leaf specialists.'
version: 1.1.0
author: Wander Labs
license: MIT
platforms:
- linux
- macos
metadata:
  hermes:
    tags:
    - dwight
    - claude-seo
    - orchestration
    - delegation
    - fan-out
    - fan-in
    internal_only: false
---

# Dwight Claude SEO fan-out

## Purpose

Use this skill for a deep or multi-specialist SEO/GEO audit. It ports the 18 Claude Code agent definitions into native Hermes specialist skills and executes them with `delegate_task`.

Architecture:

```text
Dwight parent
  -> one delegate_task(role="orchestrator")
      -> six sequential waves
          -> tasks array with maximum three leaf specialists in parallel
      -> fan-in and contradiction review
  -> parent Dwight writes final artifacts after independent verification
```

Required profile configuration:

```yaml
delegation:
  max_concurrent_children: 3
  max_spawn_depth: 2
  orchestrator_enabled: true
```

The depth is deliberately limited to two. The first child is the orchestrator; leaf specialists cannot delegate and cannot create grandchildren.

## Trigger and modes

- `demo`: foundation + indexation + content/AI, only applicable agents.
- `standard`: all always-on agents plus conditional agents backed by available evidence.
- `deep`: evaluate all 18 conditions and run every applicable specialist; skipped specialists must return a documented reason.

Do not use fan-out for a single bounded question. Route that directly to one specialist.

## Phase 0 — shared evidence, owned by parent Dwight

Before delegation, parent Dwight creates one immutable evidence bundle and a manifest containing target, normalized domain, locale, timestamp, audit mode, site type, business type, requested scope, source hashes and approval state. Deterministic/free collection precedes LLM analysis and paid calls.

For every auditable HTML page, the mandatory post-render gate runs **before delegation**:

```bash
./bin/dwight-schema-org-hook --url <URL> --mode always --evidence-dir <absolute-evidence-dir>
```

This one bounded operation writes `render.json` and `schema-validation.json` atomically, compares initial and rendered JSON-LD, and records syntax/policy findings. Default non-strict mode never aborts the wider audit because markup is invalid. A runtime failure becomes an explicit unavailable marker; it must never be silently treated as “no schema”. `--strict` is reserved for CI or a separately approved pre-publication gate.

Minimum evidence when available:

- `render.json`, with raw/rendered hashes and bounded render diagnostics;
- `schema-validation.json`, with raw/rendered JSON-LD, status, types, findings and JS-injection comparison;
- parsed page metadata and headings;
- robots.txt and sitemap artifacts;
- screenshots and visual metadata;
- GSC data for owned properties;
- explicit availability markers for unavailable PageSpeed, CrUX, GA4 or external APIs;
- DataForSEO artifacts only when an exact paid API authorization exists.

Never let specialists independently repeat crawling, rendering, web search, API calls or paid collection. Parent Dwight owns all external acquisition; leaf specialists only analyze the immutable bundle and prior normalized findings.

## Root dispatch contract

Parent Dwight loads this skill, reads `references/agent-waves.yaml`, then spawns exactly one orchestrator:

```text
delegate_task(
  role="orchestrator",
  goal="Run the Dwight Claude SEO wave orchestrator and synthesize one verified result",
  context="Load skill dwight-claude-seo-fanout. Target: ... Normalized domain: ... Evidence dir: ... Audit mode: ... Locale: fr-FR. Site type: ... Business type: ... Requested scope: ... Phase-0 paid acquisition record: false. Leaf external network and paid calls: forbidden. Production mutation: forbidden. Return a structured fan-in result to parent Dwight."
)
```

The parent must include absolute paths because subagents have no conversation memory. The parent does not reset or close the session while orchestration is running.

## Orchestrator workflow procedure

1. Load `references/agent-waves.yaml`, `references/schema-validation.schema.json`, `references/specialist-result.schema.json` and `references/fan-in-result.schema.json`.
2. Validate required root context, validate `schema-validation.json` against its schema (or require an explicit runtime-unavailable marker), and verify every SHA-256 in the immutable evidence manifest before dispatch.
3. Follow `depends_on_waves` in manifest order. Apply the selected mode, always launch `mode: always` specialists, and document why each conditional specialist is launched or skipped.
4. Call `delegate_task` with a tasks array containing maximum three items and `role: leaf` per task.
5. Every leaf context must include specialist skill, primary skill, target, normalized domain, audit mode, locale, site type, business type, specialist scope, FLOW stage or `not_applicable`, immutable evidence directory, dependency findings, phase-0 acquisition record and output schema.
6. Explicitly deny leaf network, web search, crawling, rendering, external APIs, MCP calls, paid calls, file writes, production mutation and further delegation. Parent Dwight owns all acquisition in phase 0.
7. Validate every returned object against `specialist-result.schema.json`: exact specialist/upstream pair, status, score rule, non-empty strings, evidence/source arrays, `paid_calls: []`, `production_mutations: []`, and resolvable evidence IDs. Record invalid output as an error; never silently coerce it to valid.
8. Wait for the complete batch, mark failed or invalid leaves, and continue to the next wave. One failed specialist must not block the rest of the audit.
9. Carry only normalized findings and evidence IDs into later waves; do not paste full transcripts.
10. After the last wave, perform fan-in: deduplicate findings, resolve contradictions, separate facts/inferences/unavailable data, preserve provenance and recalculate heuristic priorities.
11. Return one object matching `fan-in-result.schema.json` to parent Dwight. Do not write public or production outputs.

## Leaf task template

```text
Goal: Act as <specialist_name> for a read-only SEO/GEO audit.
Context:
- Load skill <specialist_name> and primary skill <primary_skill>.
- Target: <url>
- Normalized domain: <domain>
- Audit mode: <demo|standard|deep|integration-smoke>
- Locale: fr-FR / France
- Site type: <service|content|ecommerce|local|marketplace|other>
- Business type: <explicit description>
- Specialist scope: <bounded scope>
- FLOW stage: <FIND|LEVERAGE|OPTIMIZE|WIN|LOCAL|not_applicable>
- Evidence dir: <absolute path>
- Evidence manifest: <absolute path>
- Post-render evidence: <absolute path>/render.json
- Schema hook evidence: <absolute path>/schema-validation.json
- Phase-0 acquisition record: <absolute path or none>
- Dependencies: <normalized prior findings only>
- Leaf network/API/paid calls: forbidden
- File and production mutation: forbidden
- Output: JSON only matching specialist-result.schema.json
```

## Cost, isolation and safety gates

- Parent Dwight may acquire paid evidence only when the root request names API, operation and exact cap; that acquisition is completed and recorded before fan-out.
- Leaf specialists never call DataForSEO, Google, Maps, MCP, web search or any external API. `paid_calls` is always empty for leaves.
- No production mutation is permitted inside an audit wave.
- No WordPress edit, publication, indexing submission, email, CRM action, credential change, installation, screenshot capture, baseline creation or shared-file write.
- Workers cannot contact the user; missing information becomes a limitation.
- `subagent_auto_approve` remains false; concurrency is three, depth is two, max iterations are 30 and child timeout is 1200 seconds.
- MCP toolsets are not inherited by children. General child tools are still not a strict read-only sandbox, so compensating controls remain mandatory: immutable evidence hashes, explicit no-write prompts, empty mutation arrays, full live tool traces and parent post-run integrity checks.

## Fan-in contract

Deduplicate on the schema fields `issue_type` + `affected_url` + `evidence_id`. When specialists disagree, preserve both claims, compare evidence quality and mark unresolved contradictions. Never average incompatible scores blindly.

Final findings use the client-ready format:

- preuve;
- impact;
- priorité;
- action;
- indicateur avancé;
- test de falsification;
- confiance;
- spécialiste source.

The final report must state which of the 18 specialists completed, were partial, blocked or skipped, plus every unavailable data source, every phase-0 paid acquisition and every specialist error.

## Verification

Before writing the final report, parent Dwight must:

1. validate every leaf result and the fan-in object against their JSON schemas;
2. verify every evidence ID and source path, not a sample;
3. recompute every evidence SHA-256 and compare it with the immutable manifest;
4. inspect delegation manifests/live traces for forbidden network, paid, write, mutation or nested-leaf tool calls;
5. verify `paid_calls` and `production_mutations` are empty for every leaf;
6. report any failed validation as a limitation rather than silently repairing the claim.

Subagent summaries are evidence to review, not proof by themselves. Parent Dwight remains the only writer of final artifacts.
