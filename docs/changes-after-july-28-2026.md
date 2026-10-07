# Change inventory after the July 28, 2026 baseline

Baseline: `974819083e2b07336d2f8a8ca0a07ba8afeb82c0` (July 28, 2026 17:53 +04:00)
Inventory captured from: `24fcb7f9b3cebc0085aca5f48cc22e7d2e3e6666` (October 7, 2026)
There are 113 commits after the selected baseline. This file is retained across the rollback so important changes can be selectively reapplied.

## Main changes to review before reintroducing

- Generation/runtime foundations: brand-asset extraction, immutable generation-run lineage, rollout lifecycle, workerless/parallel generation, generation retries and recovery, generation contracts, Bedrock fallback handling, Cloudflare-specific generation, and restored Bedrock Sonnet fallback routing.
- Content and design changes: industry/copy safeguards, extraction of contact and service details, hero/media contracts, placeholder normalization, source-backed fallback output, and post-processing to preserve approved copy. Some October post-processing currently appends missing copy/services/CTA after the page body content, producing the large text block reported for Green Leaf.
- Preview and QA behavior: runtime QA, screenshot/visual QA, compiler/runtime checks, stricter readiness gating, static artifact delivery, CSP hardening, and the Oct 7 preview bypass for complete-but-QA-blocked artifacts.
- Product changes: client comparison/share galleries, per-lead booking links, social preview metadata, client-link compatibility, and lead workspace UI updates.
- Security and operations: owner-scoped lead/site APIs, credential-commit prevention, permanent lead deletion, build-version health reporting, Celery worker deployment fixes, CI checks, and generation diagnostics.

## Reapply carefully before multi-user production use

The July 28 snapshot predates owner scoping for lead/site APIs (`41a8744`, `72c1e74`) and credential-commit prevention (`112bbc1`). It also predates later deletion safeguards and operational hardening. Treat those as priority candidates for selective reapplication before exposing the application broadly. Review compatibility instead of cherry-picking blindly.

## Rollback compatibility adjustment

The July 28 settings model expected Bedrock fallback model IDs as a JSON list, while the current production `.env.production` stores the same IDs as a comma-separated value. The rollback branch keeps the existing production setting intact and parses either representation in `config.py`; `bedrock_client.py` consumes the normalized list.

## Chronological commit ledger

- `d4b4088` (2026-08-31) Complete brand asset extraction and runtime QA
- `5e3f8f8` (2026-08-31) Allow persisted static previews in public sharing
- `11327dc` (2026-08-31) Penalize runtime failures in visual QA
- `f1387bc` (2026-08-31) Add immutable generation run lineage
- `792a33a` (2026-08-31) Harden generation run rollout lifecycle
- `e033e97` (2026-08-31) Finalize failed runtime QA tasks
- `41a8744` (2026-08-31) Scope site APIs to owning users
- `72c1e74` (2026-08-31) Enforce owner scoping for lead and site APIs
- `b024727` (2026-08-31) Expose variant comparison and client sharing
- `dfd4184` (2026-08-31) fix public variant galleries and logo fallback
- `a90e037` (2026-08-31) clarify public variant gallery copy
- `0bbc774` (2026-08-31) resolve relative logo assets during extraction
- `fac07ca` (2026-08-31) allow unlimited client variant galleries
- `669ff96` (2026-08-31) allow legacy previews in client gallery selection
- `84b7862` (2026-08-31) fix missing SiteSection generation import
- `7f7b442` (2026-08-31) escape literal component imports in generation prompt
- `9a9466a` (2026-08-31) add client-facing variant titles and descriptions
- `6c44ab3` (2026-08-31) fix master brief quality scoring
- `3d1593d` (2026-08-31) make quality score brief fields compatible
- `4bb5f5c` (2026-08-31) guard optional quality score fields
- `f999c7e` (2026-09-01) fix static preview runtime and asset guards
- `d5795e2` (2026-09-01) expose deployed build version in health
- `7cdb82a` (2026-09-01) add factual asset and variant generation guards
- `8c9f16d` (2026-09-01) test factual generation guards
- `da622d2` (2026-09-01) fix production Gemini client compatibility
- `e0cc8ef` (2026-09-01) extract contact details from source markup
- `112bbc1` (2026-09-01) prevent credential commits
- `4a0f0ab` (2026-09-01) enforce deterministic contact and footer guards
- `cd20c1f` (2026-09-01) Add per-lead booking links to redesign pages
- `afa2f1e` (2026-09-01) fix structured contact extraction and font labels
- `56436b8` (2026-09-01) persist extraction contacts and inferred industry
- `a38365b` (2026-09-01) avoid boolean evaluation of motor database
- `3007904` (2026-09-01) deploy versioned celery worker consistently
- `35db9c0` (2026-09-01) recompute contacts at extraction persistence boundary
- `0dfbf8a` (2026-09-01) rescan empty structured contacts before persistence
- `f834728` (2026-09-01) Expose persisted contact info in extraction snapshots
- `1a44c55` (2026-09-01) Fix master brief retrieval route
- `cb7ffde` (2026-09-01) Add source-backed static fallback when LLM is unavailable
- `2b40ae2` (2026-09-01) Sanitize fallback CTA and include logo asset
- `98bbb96` (2026-09-01) Replace inherited contact placeholders in fallback HTML
- `a582cb8` (2026-09-01) Switch main AI provider to Cloudflare Workers AI
- `a743e52` (2026-09-02) Fix per-lead booking URL persistence
- `6e8ce3e` (2026-09-02) Enable safe parallel lead generation
- `83904a4` (2026-09-02) Harden split HTML generation and remove queue workers
- `aa30660` (2026-09-02) Disable reasoning for Cloudflare artifact generation
- `44adb6d` (2026-09-02) Run screenshot QA without a task queue
- `5626bdf` (2026-09-02) Keep screenshot capture async in workerless mode
- `b995929` (2026-09-02) Fix static generation truthfulness and previews
- `69eb593` (2026-09-02) Pin latest generation run for runtime QA
- `90e2076` (2026-09-02) Include Node runtime for static JavaScript validation
- `770d956` (2026-09-02) Clear stale pipeline detail after generation
- `95a82a9` (2026-09-02) fix: use working Cloudflare vision model
- `5f53e11` (2026-09-02) fix: pin production vision model
- `3ee079b` (2026-09-02) fix: use multimodal chat for vision QA
- `8057d16` (2026-09-02) fix: keep variant content industry accurate
- `0e78888` (2026-09-02) feat: generate preview copy from brief
- `bec12df` (2026-09-02) fix: keep redesign links usable after variant removal
- `f5f8e4d` (2026-09-02) fix: allow archived preview slugs to be reused
- `8053166` (2026-09-02) fix: restore coherent static site generation
- `15d740f` (2026-09-03) feat: add permanent lead deletion
- `374b594` (2026-09-03) fix generated site assets and visual QA
- `7ee9ea7` (2026-09-03) fix dark logo contrast on dark variants
- `46fa682` (2026-09-03) Complete site generation remediation phases
- `5627f42` (2026-09-03) Stabilize backend CI lint gate
- `f801f6d` (2026-09-03) Expose deployed build version in backend image
- `950348d` (2026-09-03) Close runtime eligibility and bundle isolation gaps
- `95966a9` (2026-09-03) Fix brief auto-approval pipeline errors
- `51a83ab` (2026-09-03) Preserve lead URL through login redirect
- `84b2046` (2026-09-03) Let auto pipeline use safe brief fallbacks
- `abf209e` (2026-09-03) Recover auto pipeline from partial extraction gaps
- `a82275f` (2026-09-03) Recover failed static site variants safely
- `1493fb8` (2026-09-03) Retry malformed generated variants concisely
- `8d41b6e` (2026-09-03) Harden multi-variant site generation
- `fbf9e0f` (2026-09-03) Prevent lead loading hangs and preserve generation diagnostics
- `ebd4a01` (2026-09-03) Harden static variant generation retries
- `7845eb3` (2026-09-04) Harden site generation contracts and preflight
- `a318b2c` (2026-09-05) Restore Bedrock design generation path
- `f19df93` (2026-09-05) Restore historical variant identities
- `e5a07cd` (2026-09-05) Restore direct historical design guidance
- `fa5ae2f` (2026-09-05) Keep asset download and S3 storage fixes
- `d30522e` (2026-09-05) Tighten Cloudflare HTML generation budget
- `60a533e` (2026-09-05) Normalize generated resource URLs before validation
- `fe096b1` (2026-09-05) Add Cloudflare-specific artifact generation path
- `bcb41e7` (2026-09-05) Normalize Cloudflare media markers for typography variants
- `2bcab45` (2026-09-11) Fix legacy client redesign links
- `51a5db5` (2026-09-11) Keep selected client variants after QA warnings
- `7846338` (2026-09-11) Document durable public client link policy
- `f43ac39` (2026-09-11) Add social preview metadata to redesign links
- `812ce13` (2026-09-11) Serve redesign social images from same origin
- `2136cf5` (2026-09-11) Keep selected public previews available after QA warnings
- `e7e2ee7` (2026-09-23) Restore Bedrock Sonnet generation with model fallbacks
- `e392751` (2026-09-30) Harden website generation and hero creative contracts
- `270e8a4` (2026-09-30) Normalize safe provider HTML artifacts
- `35266f2` (2026-09-30) Normalize provider font choices
- `7ce8376` (2026-09-30) Harden live HTML generation recovery
- `3965c8a` (2026-09-30) Normalize provider placeholder domains
- `39b9fe1` (2026-09-30) Close live CTA and hero contract gaps
- `15c110e` (2026-09-30) Normalize remaining provider placeholders
- `97e8503` (2026-09-30) Narrow typography-only hero media validation
- `bd70908` (2026-09-30) Narrow proof evidence validation to proof containers
- `f94252e` (2026-09-30) Restore approved copy in provider HTML artifacts
- `f66fbc8` (2026-09-30) Normalize remaining provider content placeholders
- `9d51f2d` (2026-09-30) Restore extracted service content in HTML artifacts
- `1f93ccb` (2026-09-30) Normalize extracted content and placeholders everywhere
- `4deef60` (2026-10-07) Fix cleanup for unsupported quote blocks
- `853cd2a` (2026-10-07) Preserve approved copy during proof cleanup
- `660636e` (2026-10-07) Skip proof-only fallback without evidence
- `cb37d28` (2026-10-07) Recover minor generated HTML defects
- `079bdea` (2026-10-07) Ignore misclassified business hours during generation
- `d2096e7` (2026-10-07) Restore approved service copy in service section
- `f99b458` (2026-10-07) Remove unsupported bare quote blocks
- `cf8d5a4` (2026-10-07) Allow previewing generated sites pending QA
- `24fcb7f` (2026-10-07) Allow blocked artifacts in operator previews
