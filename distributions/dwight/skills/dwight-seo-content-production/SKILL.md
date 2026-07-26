---
name: dwight-seo-content-production
description: "Use when Dwight creates or improves a sourced SEO brief, outline, article, landing-page copy, title, meta, FAQ, internal links or editorial QA package."
version: 0.1.0
author: Wander Labs
license: Proprietary
metadata:
  hermes:
    tags: [dwight, seo, content, brief, article, editorial-qa]
---

# Dwight SEO Content Production

Use this skill to produce reader-first content that is useful, differentiated and ready for human validation.

## Inputs

Read `local/CLIENT.md`, the current Brand Voice Guide when available, the target page, relevant source material and the applicable silo plan. Do not read an entire client corpus when targeted files are sufficient.

Identify:

- audience and reader problem;
- business objective and conversion stage;
- primary intent and page type;
- main topic and supporting questions;
- required evidence and first-hand expertise;
- deliverable: brief, outline, draft, rewrite or QA.

## Content workflow

1. Frame the reader's real problem before keywords.
2. Inspect existing content and cannibalization risk.
3. Research facts and competitor coverage when the page is strategic.
4. Separate verified facts, client experience and editorial synthesis.
5. Define a specific angle and promise.
6. Build a logical H1/H2/H3 progression.
7. Draft with short paragraphs, concrete examples and natural transitions.
8. Add only useful SEO assets:
   - concise slug;
   - meta title and description;
   - FAQ based on real questions;
   - contextual internal links;
   - descriptive alt text;
   - soft, relevant CTA.
9. Apply the active Brand Voice Guide.
10. Run editorial, factual and SEO QA.

## Brief output

```markdown
## Objectif et audience
## Intention et angle
## Sujet principal et champ lexical
## Sources et preuves nécessaires
## H1, slug, title et meta
## Plan H2/H3
## FAQ
## Maillage interne
## Images et alt text
## Checklist de validation
```

Return only the requested level of detail. Do not write a full article when the user asked for a brief.

## Writing rules

- Reader value comes before keyword density.
- Use original phrasing; do not remix competitor sentences.
- Avoid generic AI openings, inflated promises and filler.
- Never invent case studies, quotes, credentials, awards, prices or statistics.
- If exact internal URLs are unknown, discover them or label the destination; do not invent URLs.
- Preserve useful client ideas during rewrites instead of flattening them into a template.

## Sécurité et guardrails

- Drafting is not publication.
- Any CMS write, file write outside the requested deliverable, public action or deletion requires the proper validation.
- Do not expose confidential client notes or source text in the final content.
- Attribute regulated, legal, medical or high-stakes claims to appropriate sources and state limits.

## Vérification

Before delivery:

- [ ] Audience, intent and business objective are clear.
- [ ] The angle is specific and evidence-backed.
- [ ] The active Brand Voice Guide was applied when present.
- [ ] Headings progress logically.
- [ ] SEO assets are natural and complete when requested.
- [ ] Facts and URLs were verified.
- [ ] No generic filler, plagiarism or fabricated proof remains.
- [ ] Status is clearly draft/brief unless publication was separately approved and verified.
