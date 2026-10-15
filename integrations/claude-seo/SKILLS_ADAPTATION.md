# Claude SEO skills adaptation

The directory `distributions/dwight/skills/claude-seo-upstream/` starts from the 25 upstream skills in `AgriciDaniel/claude-seo` release `v2.2.4`, commit `6b63c8bb7b2e8e4480060604555e3af629b54c2c`.

The upstream source tree hash before adaptation is recorded as `upstream_source_skills_tree_sha256` in `upstream.yaml`. The installed, adapted tree hash is recorded separately as `upstream_skills_tree_sha256`.

Exactly one change class is applied to every vendored `SKILL.md`: a `Hermes client-safety overlay` immediately after frontmatter. It makes the upstream method subordinate to Dwight Core and requires:

- the client-safe adapter and active client context;
- only profile-isolated launchers;
- explicit approval for environment installation or credential setup;
- a capped preauthorization or exact approval for paid calls;
- exact approval for external persistent mutations;
- read-only specialists and parent-owned acquisition/writes during fan-out.

The executable runtime under `runtime/` is the selected upstream core with development files, Git metadata, Claude-specific agents/hooks, screenshots, changelog and optional extensions excluded. `requirements.upstream.txt` preserves the original dependency ranges; `requirements.txt` pins the 17 direct dependencies smoke-tested for this RC. Their pre- and post-adaptation tree hashes are independently locked in `upstream.yaml`.

`runtime-policy.yaml` classifies every bundled Python script exactly once. Credential setup, paid DataForSEO merchant calls, IndexNow/Google indexing submission, source mutation, unpinned FLOW sync, dynamic `npx`, and maintainer-only release scripts are blocked by the client wrapper.
