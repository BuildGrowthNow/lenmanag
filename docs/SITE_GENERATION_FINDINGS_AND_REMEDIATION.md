# LenQuant Site Generation: Findings and Phased Remediation Plan

## Purpose

This document is an implementation brief for another AI or engineering agent. It explains why the latest Get It Done Home Improvements generation produced two visually incomplete variants and one failed variant, and it defines the changes needed to make LenQuant's principal HTML generation path produce richer, reliable, modern websites.

This document records the remediation boundary. The implementation and tests are maintained in the repository; no production configuration, database records, deployed services, or Get It Done site artifacts were changed as part of this work.

## Non-negotiable product direction

The principal output remains HTML: `html_v1`, `html_v2`, and `html_v3` must continue to produce complete semantic HTML documents.

However, “HTML” must no longer mean “vanilla-only.” The HTML path must be able to use, when appropriate:

- Three.js and/or `@react-three/fiber` for justified WebGL experiences.
- GSAP and ScrollTrigger for choreographed motion.
- Lenis for smooth scrolling when it materially improves the concept.
- React for interactive islands embedded in an otherwise semantic HTML document.
- shadcn/Radix components for accessible interactive UI.
- Embla or an equivalent tested carousel implementation.
- Framer Motion when a React island needs it.
- High-quality native CSS, SVG, canvas, and JavaScript equivalents when a library is unnecessary or too costly.

The final published artifact should remain:

1. A complete semantic HTML document.
2. A same-origin compiled CSS bundle.
3. A same-origin compiled JavaScript bundle.
4. An explicit capability/dependency manifest.
5. A readable and usable no-JavaScript fallback.

Do not solve this by hotlinking arbitrary CDN scripts. Dependencies must be allowlisted, version-pinned, compiled by LenQuant, and hosted through the existing asset delivery system.

---

## 1. Incident identity and evidence

### Production identifiers

- Displayed job prefix: `434950d45b8f`
- Full production job ID: `434950d45b8f4a3e90e0fc2113915c7a`
- Lead ID: `82f48f0e5f7c4f9fa6bf203cf96a76cb`
- Generation run ID: `07495be4faae4173b30e1799f45b9c4e`
- Extraction ID: `c9fbd456398c4025ac0ecf3251a5e2d9`
- Master brief ID: `b03a2199-37bb-4135-9b56-5386931ce403`
- Production commit during the run: `7ee9ea7`
- Run start: `2026-09-02 21:49:34 UTC`
- Run finish: `2026-09-02 22:05:28 UTC`
- Final job status: `partial`
- Final job step: `Runtime QA found variant failures`

### Evidence inspected

- The two user-supplied full-page screenshots.
- Production Mongo records for the job, generation run, extraction, brief, and generated sites.
- Production backend logs for the failed variant.
- The saved HTML for `html_v1` and `html_v2`.
- The saved CSS and JavaScript bundles for both successful artifacts.
- Runtime and screenshot QA stored on both generated sites.
- Current local/production repository implementation at commit `7ee9ea7`.
- Relevant generation, validation, extraction, compiler, and QA tests.

### Evidence limitation

The rejected `html_v3` source was not persisted. Its exact failing element cannot be inspected. Production logs do confirm this sequence:

1. The first `html_v3` provider response was incomplete and triggered the incomplete-artifact retry.
2. The retry produced a parseable artifact.
3. Validation rejected the artifact for an unapproved testimonial or review.
4. The correction pass also retained prohibited testimonial/review semantics.
5. The variant was rejected with `document_validation_failed`.

Persisting rejected artifacts privately is a Phase 0 requirement below.

---

## 2. Executive diagnosis

This incident is not primarily a prompt-quality problem. It is a pipeline contract failure across configuration, extraction, brief generation, capabilities, validation, and QA.

The critical causal chain was:

1. The crawler found the real company logo and dozens of real project images.
2. Production had `asset_download_enabled=false` even though S3 asset storage was configured.
3. Because the render policy only allows cached/approved assets, the real logo and photos were excluded from the approved brand snapshot.
4. The frozen generation snapshot contained:
   - `logoUrl: null`
   - `logoLightUrl: null`
   - `logoDarkUrl: null`
   - `logoVariants: []`
   - `imageUrls: []`
   - `imageInventory: []`
5. The auto-approved master brief nevertheless demanded multiple photo-driven sections and invented specific testimonial and project-location content.
6. The HTML generator was instructed to produce an Awwwards-quality experience but was explicitly forbidden from using Three.js, GSAP, Lenis, React, shadcn, or other third-party runtimes.
7. With no approved media and a restricted runtime, the model substituted empty geometric panels, generic SVG shapes, magnetic-button logic, and simple IntersectionObserver reveals.
8. The validators checked basic document structure and factual safety, but did not require:
   - a footer landmark;
   - a hero image when the design contract required one;
   - a functional carousel;
   - meaningful animation;
   - non-empty project media;
   - evidence-linked proof content.
9. `html_v1` and `html_v2` were saved, but both failed runtime QA and were marked blocked.
10. `html_v3` attempted to implement unsupported testimonial/review content originating in the approved brief and was correctly rejected by the final safety gate.

The fix must start upstream. Do not weaken the testimonial validator merely to make the third variant pass.

---

## 3. Confirmed production findings

### 3.1 Asset downloading was disabled in production

Production settings during the investigation:

- `asset_download_enabled=false`
- `asset_storage_backend="s3"`
- S3 bucket configured: yes
- LLM provider: Cloudflare

The crawl manifest contained the real logo:

- `http://www.getitdonehomeimprovements.com/img/gid-home-improvements-logo.png`

It also contained many real project images, including remodeling, kitchens, bathrooms, carpentry, decks, siding, gutters, masonry, and before/after project photography.

Therefore, the missing logo and imagery were not caused by a source website without assets. They were caused by the production caching feature being disabled while the generation validator required cached assets.

### 3.2 The frozen brand snapshot was empty

The job snapshot recorded no usable brand assets:

```text
logoUrl: null
logoLightUrl: null
logoDarkUrl: null
logoVariants: []
imageUrls: []
imageInventory: []
approvedImageInventory: []
rejectedImages: []
```

The absence of both approved and rejected images is especially important. The system did not distinguish “no source imagery exists” from “imagery was discovered but caching was disabled.” Those states must be different.

### 3.3 The palette was also not faithful to the source

The frozen palette was:

- Primary: `#6366f1`
- Secondary: `#f1ee62`
- Accent: `#f16265`

The extraction had mostly generic computed colors such as black, white, browser-link blue, and transparent values. The generated indigo/purple palette was therefore a fallback inference, not a faithful brand extraction.

The source logo and source site should have been used to validate the palette before auto-approval.

### 3.4 The master brief contradicted the available evidence

The master brief had `missingRequirements: []` and was auto-approved even though it required:

- A full-bleed image of a renovated kitchen in the hero.
- Foreground tools, a mid-ground room, and background blueprint lines.
- Photos that expand on hover in the process section.
- A horizontal gallery of real project photos.
- A happy-homeowner background image in the CTA.
- A custom drafting-pencil cursor with a trail.
- Magnetic buttons.
- 3D tilt.
- Parallax layers.
- Morphing shapes.

At approval time, the snapshot had no approved logo and no approved images. This brief should have been blocked or explicitly converted to an approved typography-only concept.

### 3.5 The master brief invented proof content

The auto-approved social-proof section requested:

- A Ridgewood homeowner testimonial about a kitchen remodel.
- A Wayne homeowner testimonial about gutter cleaning and repair.
- A Montclair homeowner testimonial about exterior painting.
- Star ratings.
- Project-type badges.

Those exact proof items were not present in the approved evidence snapshot.

The brief also requested gallery items in Paramus, Clifton, Oakland, and Franklin Lakes. The source extraction contained genuine project information, but these specific gallery locations/descriptions were not proven by the approved evidence shown to generation.

This is the upstream cause of the `html_v3` validation failure. The final validator correctly refused unsupported testimonial/review content, but the content should never have passed brief approval.

### 3.6 The source already had a proper footer

The crawl captured source-backed footer information including:

- Company phone and email.
- New Jersey contractor license number.
- Service area.
- Home, services, work, testimonials, FAQ, about, and contact navigation.
- Privacy Policy.
- Terms and Conditions.
- Copyright information.
- Location information.

Both generated variants contained no `<footer>` element at all.

This was not a missing-data problem. It was a brief/generation/validation problem.

### 3.7 `html_v1` production result

Saved site:

- Site ID: `102d9846-72b4-45fa-867f-0882cca4f8af`
- Preview slug: `get-it-d-v1`
- Preview URL: `https://sites.lenquant.com/st/get-it-d-v1`
- Readiness status: `blocked`
- QA status: `fail`
- Final quality score field: `0`
- Vision critique score: `78`

Structural inspection:

- `<img>` count: `0`
- `<footer>` count: `0`
- Carousel implementation: none
- Three.js: none
- GSAP: none
- Lenis: none
- React: none
- Magnetic behavior: present in JavaScript
- Generic IntersectionObserver reveal behavior: present

Runtime QA failure:

- `mobile_menu_failed`

Vision QA explicitly identified the project section as empty dark boxes and a significant failure point.

### 3.8 `html_v2` production result

Saved site:

- Site ID: `f6bf30cc-7c2f-4daa-8fe2-ab3c5ed49726`
- Preview slug: `get-it-d-v2`
- Preview URL: `https://sites.lenquant.com/st/get-it-d-v2`
- Readiness status: `blocked`
- QA status: `fail`
- Final quality score field: `0`
- Vision critique score: `68`

Structural inspection:

- `<img>` count: `0`
- `<footer>` count: `0`
- Carousel implementation: none
- Three.js: none
- GSAP: none
- Lenis: none
- React: none
- Magnetic behavior: present in JavaScript
- Generic IntersectionObserver reveal behavior: present

Runtime QA failure:

- `content_hidden_after_scroll`
- Two elements remained hidden after the QA scroll.

Vision QA identified placeholder circles/lines in the project area and a missing social-proof section.

### 3.9 “Generated” did not mean “usable”

The pipeline emitted an event saying two usable variants were generated, but runtime QA later marked both saved variants blocked.

Terminology should be corrected:

- `artifact_generated`: provider output was parsed and stored.
- `document_validated`: static/compile validation passed.
- `runtime_qa_passed`: runtime interactions and rendering passed.
- `visual_qa_passed`: visual requirements passed.
- `publishable`: all hard gates passed.

Do not call an artifact “usable” before runtime and required visual gates pass.

### 3.10 QA contains a policy conflict

Vision QA correctly detected missing images. However, its recommendation for the proof section suggested adding avatars/testimonials.

That recommendation is unsafe when no approved testimonial evidence exists.

Vision/LLM QA recommendations must pass through the same evidence policy as generation. They may recommend:

- showing verified license information;
- showing verified service area;
- linking to the source testimonials page;
- showing real project imagery;
- using a process/credentials block;

They must not recommend creating new testimonials, ratings, logos, metrics, or people.

---

## 4. Code-level causes

### 4.1 Static HTML generator forbids the required modern runtime

Primary file:

- `apps/backend/app/core/static_html_generator.py`

Relevant behavior around the current prompt:

- Requires exactly three code blocks: HTML, CSS, JavaScript.
- Requires vanilla JavaScript only.
- Explicitly forbids Three.js, GSAP, Lenis, and other libraries.
- Does not compile a dependency manifest.
- Does not support React islands or shadcn components.

This directly conflicts with the product requirement that principal HTML variants be modern, rich, and capable of “wow” interactions.

### 4.2 A richer compiler exists, but is disconnected from principal HTML

Relevant files:

- `apps/backend/app/core/ai_site_generation.py`
- `apps/compiler/src/compile.ts`
- `apps/compiler/src/virtual-modules-plugin.ts`
- `apps/compiler/src/validate.ts`
- `apps/compiler/package.json`

The compiler already supports or includes:

- React.
- Framer Motion.
- GSAP.
- Lenis.
- Embla.
- Lucide.
- Tailwind.
- A limited virtual shadcn surface.

Current shadcn primitives are limited to:

- Button.
- Card.
- Badge.
- Separator.

Three.js is not currently included.

The solution is not to abandon HTML. The solution is to reuse/extend this bundling capability behind the HTML generator.

### 4.3 Asset promotion is correctly fail-closed but lacks preflight

Relevant files:

- `apps/backend/app/core/extraction.py`
- `apps/backend/app/core/asset_downloader.py`
- `apps/backend/app/core/asset_metadata.py`
- `apps/backend/app/core/master_brief.py`
- `apps/backend/app/core/static_html_generator.py`

Current behavior:

1. Crawl discovers assets.
2. Assets are cached only if downloading is enabled.
3. Master brief promotes only cached render URLs.
4. HTML validator rejects unapproved remote render assets.

The fail-closed render policy is correct. The missing part is a preflight gate that stops premium generation when source assets exist but caching/promotion did not happen.

### 4.4 Logo detection found the logo, but the asset never became usable

The extraction contained high-confidence logo cues for the real logo. Some cues were relative URLs and others were absolute HTTP URLs.

Because caching was disabled, `get_cached_asset_url()` returned no usable render URL and `brandAssets.logoUrl` remained null.

Fixing logo ranking alone will not solve this incident. Production asset caching and URL resolution must be fixed first.

### 4.5 Hero image validation checks occurrence, not role or placement

The static validator currently verifies that an approved image URL appears somewhere in the HTML when approved images exist.

It does not verify:

- that the image is in the hero;
- that it has the `hero` asset role;
- that it occupies a meaningful visual area;
- that it loads and has nonzero dimensions;
- that the crop is appropriate;
- that a typography-only decision was explicitly approved;
- that a geometric media shell is not empty.

### 4.6 Footer validation does not require a footer

`_enforce_footer_year()` only updates/adds copyright text if a footer already exists.

The document validator does not require `<footer>`.

Therefore both saved variants passed document validation without any footer landmark.

### 4.7 Motion initialization is not motion quality

`_apply_static_safety_layer()` appends a generic IntersectionObserver reveal and optional float effect to generated pages.

The runtime flag is set after this generic layer initializes.

This proves only that setup code ran. It does not prove:

- the art-direction motion was implemented;
- the animation is perceptible;
- the animation completes;
- the animation is tasteful;
- the page has a signature transition;
- hidden content is eventually revealed;
- magnetic/cursor behavior is appropriate;
- reduced-motion behavior is correct for every component.

Production `html_v2` demonstrates the failure: runtime initialization was true while two elements remained hidden after scroll.

### 4.8 Carousel behavior is not generated or tested

The static path has no enforced carousel recipe or component.

Runtime QA does not:

- identify carousels;
- click next/previous;
- drag slides;
- test keyboard navigation;
- confirm active index changes;
- test autoplay pause;
- test reduced motion;
- test screen-reader semantics;
- confirm all slides remain accessible without JavaScript.

The two production bundles contain no carousel implementation.

### 4.9 Testimonial validation is downstream and substring-based

Relevant functions:

- `_approved_testimonial_quotes()`
- `_has_testimonial_markup_without_approved_quote()`

The current validator scans the lowercased HTML for markers such as:

- `testimonial`
- `review`
- `customer quote`
- `what clients say`
- `said by`

If any marker appears and no complete approved quote appears verbatim, the page is rejected.

This is useful as a last safety gate, but insufficient as the primary model:

- It can trigger on class names, IDs, comments, or accessibility labels.
- It does not reason about evidence IDs.
- It does not catch every form of fake social proof.
- It cannot explain exactly which element caused failure.
- The single repair attempt can leave a hidden marker behind.

The brief generator and brief approval gate must prevent unsupported proof earlier.

---

## 5. Target enhanced-HTML architecture

### 5.1 Output contract

Change `html_v1`, `html_v2`, and `html_v3` from three unconstrained raw blocks to an `EnhancedHtmlPackage`.

Suggested logical schema:

```text
EnhancedHtmlPackage
  htmlShell
  cssEntry
  scriptEntry
  capabilityManifest
  interactionManifest
  assetBindings
  evidenceBindings
  fallbackPlan
```

#### `htmlShell`

- Complete `<!doctype html>` document.
- Semantic landmarks.
- All core content server-rendered/static in the HTML.
- Explicit mount roots for optional React islands.
- No dependency on JavaScript for essential reading or conversion paths.
- No arbitrary external scripts/styles.

#### `cssEntry`

- Generated CSS/Tailwind entry.
- Component/island CSS.
- Responsive rules.
- Reduced-motion rules.
- Fallback states.
- No inaccessible hidden initial states without progressive enhancement.

#### `scriptEntry`

- TypeScript or JavaScript module.
- Native interactions and/or island bootstrap.
- Imports only from the approved capability manifest.
- No raw CDN imports.
- No `eval`, `new Function`, or string timers.
- Calls readiness only after all declared required interactions bind successfully.

#### `capabilityManifest`

Example fields:

```text
manifestVersion
allowedPackages[]
requestedCapabilities[]
selectedCapabilities[]
nativeRecipes[]
reactIslands[]
bundleBudgets
fallbackRequirements
```

#### `interactionManifest`

Every nontrivial interaction must declare:

```text
id
type
rootSelector
controlSelectors
initialState
expectedStateChanges
keyboardContract
touchContract
reducedMotionContract
fallbackBehavior
requiredForReadiness
```

This manifest is what runtime QA must execute.

### 5.2 React and shadcn as HTML islands

React must be optional at component level, not mandatory for the whole document.

Good React-island candidates:

- Accessible carousel.
- Before/after comparison.
- Dialog/sheet estimate form.
- Tabs/accordion for services or FAQ.
- Configurator or estimator.
- Complex Three.js scene using `@react-three/fiber`.
- Stateful gallery filters.

Poor React-island candidates:

- Plain navigation links.
- Static hero copy.
- Simple hover cards.
- Basic reveal animations.
- A footer.
- Decorative gradients.

This preserves fast semantic HTML while enabling shadcn/Radix where it helps.

### 5.3 Native equivalents are first-class

The agent must not import libraries merely to satisfy a technology checklist.

Use tested native recipes for:

- CSS scroll-driven animations when browser support/fallback is acceptable.
- IntersectionObserver reveals.
- CSS perspective/tilt.
- Native horizontal scroll with snap points.
- Lightweight carousel behavior.
- Sticky storytelling.
- SVG path drawing.
- Canvas particles when WebGL is unnecessary.
- Pointer-driven magnetic hover with strict limits.

The acceptance gate is the experience contract, not the library name.

### 5.4 Three.js policy

Three.js should be available, not mandatory on every site.

Require all of the following before selecting it:

- The art-direction plan explains why 3D is meaningful to this business.
- A 2D fallback is defined.
- WebGL feature detection is implemented.
- Context loss is handled.
- Reduced motion disables or simplifies the scene.
- Mobile uses a simplified scene or poster fallback.
- Bundle and GPU budgets pass.
- The scene does not obstruct text, focus, navigation, or CTA use.
- Runtime QA verifies both WebGL and fallback modes.

For a home-improvement site, justified examples could include:

- A material/room transformation scene.
- A simplified exploded construction layer.
- An interactive project model when a real model exists.

Unjustified examples:

- Random floating blobs.
- Decorative spinning geometry unrelated to the brand.
- A 3D scene used only because Three.js is available.

### 5.5 GSAP and Lenis policy

GSAP is appropriate for:

- Sequenced hero choreography.
- Pinned storytelling.
- SVG drawing.
- Timeline-based transitions.
- Complex parallax with clear narrative purpose.

Lenis is appropriate only when:

- It does not break browser navigation, anchors, forms, or accessibility.
- It is disabled for reduced motion.
- It is tested on touch/mobile.
- It is integrated correctly with GSAP if both are selected.

Do not use smooth scrolling as the only “premium” feature.

### 5.6 Dependency delivery and security

- Add approved packages to the compiler image/package lock.
- Maintain a versioned package allowlist.
- Bundle dependencies with esbuild or the existing compiler.
- Upload hashed CSS/JS bundles through LenQuant's asset storage.
- Inject only LenQuant-hosted bundle URLs into the HTML.
- Add Content Security Policy compatible with generated sites.
- Produce a dependency inventory per site.
- Reject undeclared imports before publication.
- Add bundle-size and request-count budgets.

---

## 6. Required data contracts

### 6.1 Asset record

Every renderable asset should expose:

```text
assetId
role
sourceUrl
renderUrl
mimeType
width
height
aspectRatio
checksum
sourcePageUrl
altText
licenseType
licenseUrl
attribution
confidence
approvalState
rejectionReason
```

Required roles should include:

- `logo-primary`
- `logo-wordmark`
- `logo-mark`
- `logo-light`
- `logo-dark`
- `hero-landscape`
- `hero-portrait`
- `project-before`
- `project-after`
- `project-general`
- `service`
- `team`
- `location`
- `texture`
- `decorative`

### 6.2 Evidence record

Every proof-bearing item needs an evidence ID:

```text
evidenceId
type
text
sourceUrl
sourceExcerptHash
confidence
approved
approvedBy
approvedAt
```

Proof-bearing types include:

- Testimonial.
- Review.
- Rating.
- Metric.
- Award.
- Certification/license.
- Project claim.
- Project location.
- Customer/logo association.
- Guarantee.
- Pricing.

Generated HTML should reference evidence IDs with internal attributes such as `data-evidence-id`. These attributes do not need to be visible publicly but must be retained for validation and review.

### 6.3 Variant design contract

Each variant needs a concrete contract:

```text
variantType
runtimeMode
heroMode
heroAssetId
logoAssetId
footerMode
galleryMode
proofMode
motionRecipeIds[]
interactionRecipeIds[]
componentRecipeIds[]
selectedCapabilities[]
mobileBehavior
reducedMotionBehavior
performanceBudget
intentionalFallbacks[]
```

The three variants must differ materially in:

- Hero composition.
- Section rhythm.
- Media treatment.
- Signature interaction.
- Typography system.
- Motion choreography.

Changing only colors is not sufficient variation.

---

## 7. Phased implementation plan

## Phase 0: Make the incident reproducible and safe

### Goal

Stop losing failed artifacts and stop unsupported proof from reaching publication attempts.

### Tasks

1. Persist rejected HTML/CSS/JS privately after provider generation and correction.
2. Apply short retention and encryption at rest.
3. Never expose rejected artifacts through public preview routes.
4. Add rule IDs to every validation failure.
5. Record the exact failing element, selector, attribute/context, evidence comparison, and correction attempt.
6. Allow retrying only the failed variant without regenerating successful variants.
7. Add a semantic unsupported-proof sanitizer:
   - If no approved proof evidence exists, remove the complete proof block.
   - Remove related navigation links, IDs, classes, labels, scripts, and styles.
   - Do not simply rename or hide the word “testimonial.”
8. Add synthetic regression fixtures for unsupported proof cards and missing evidence IDs.
9. Correct UI terminology from “usable” to `artifact_generated` until runtime QA passes.

### Primary files

- `apps/backend/app/core/static_html_generator.py`
- `apps/backend/app/core/tasks.py`
- `apps/backend/app/core/generation_run.py`
- `apps/backend/app/core/sites.py`
- `apps/backend/tests/test_static_runtime_guards.py`
- `apps/backend/tests/test_llm_generation_safety.py`

### Acceptance criteria

- Failed `html_v3` source can be inspected privately.
- Validation output identifies a specific element/rule, not only a generic message.
- Unsupported proof is removed as a complete semantic section or rejected.
- No fake testimonial/review/rating can be published.
- A failed variant can be retried independently.
- The run is not called usable/publishable while runtime QA is failing.

## Phase 1: Restore real logo and image acquisition

### Goal

Ensure source-discovered assets become safe approved render assets before generation.

### Tasks

1. Enable `ASSET_DOWNLOAD_ENABLED` in production.
2. Add deployment/startup health reporting for asset downloading.
3. Fail premium-generation preflight when:
   - source assets were discovered;
   - asset downloading is disabled or unhealthy;
   - no assets were promoted;
   - the brief requires image-led sections.
4. Resolve relative asset URLs against each source page before caching.
5. Download source HTTP assets server-side and serve cached HTTPS URLs.
6. Validate:
   - response status;
   - MIME type;
   - decode success;
   - file size;
   - pixel dimensions;
   - checksum;
   - duplicate content.
7. Add role classification for logo and image assets.
8. Improve logo ranking with:
   - header placement;
   - repeated use across pages;
   - alt text;
   - aspect ratio;
   - intrinsic size;
   - filename;
   - nearby company name;
   - SVG title/metadata when applicable.
9. Penalize favicon/tiny-square/service icons unless no better logo exists.
10. Preserve both source and cached URLs.
11. Expose selected/rejected assets and reasons in preflight.
12. Validate refreshed synthetic extraction/brief fixtures after asset caching is enabled.

### Internet imagery workflow

Internet images are allowed only through a governed ingestion path:

1. Search using an approved provider/API.
2. Store source page, author/provider, license, attribution, and usage constraints.
3. Run safety and relevance checks.
4. Download the asset to LenQuant storage.
5. Assign a role.
6. Require operator approval initially.
7. Add it to the same approved asset manifest used for source assets.
8. Never hotlink arbitrary search-result URLs in generated HTML.

### Primary files

- `apps/backend/app/core/extraction.py`
- `apps/backend/app/core/asset_downloader.py`
- `apps/backend/app/core/asset_metadata.py`
- `apps/backend/app/core/asset_storage_s3.py`
- `apps/backend/app/core/master_brief.py`
- `apps/backend/tests/test_asset_downloader.py`
- `apps/backend/tests/test_asset_metadata.py`
- `apps/backend/tests/test_asset_retention.py`

### Acceptance criteria

- A source-backed logo is cached and selected in the synthetic fixture.
- Source-backed project images are cached and assigned roles.
- The master brief contains approved hero/project image IDs.
- A source-discovered-but-not-cached state is visible and blocking.
- Broken or zero-dimension assets never enter the master brief.
- Internet imagery cannot render until cached and approved.

## Phase 2: Build the enhanced HTML runtime

### Goal

Keep HTML as the principal output while enabling modern, compiled interactions.

### Tasks

1. Introduce `EnhancedHtmlPackage`.
2. Change the LLM output contract to:
   - HTML shell;
   - CSS entry;
   - JS/TS entry;
   - capability manifest.
3. Extend the compiler API to accept the JS/TS entry and capability manifest.
4. Bundle approved dependencies with esbuild.
5. Upload hashed bundles to configured asset storage.
6. Inject same-origin CSS/JS URLs into the final HTML.
7. Preserve inline-free CSP-compatible output.
8. Add React-island mounting support.
9. Expand virtual shadcn/Radix modules.
10. Add Three.js packages and WebGL capability handling.
11. Support GSAP/ScrollTrigger and Lenis in non-React bundles.
12. Add tested native recipe imports/helpers.
13. Produce a dependency inventory and bundle metrics.
14. Ensure no-JS HTML remains complete.

### Initial approved library surface

- `react`
- `react-dom`
- `framer-motion`
- `gsap`
- `gsap/ScrollTrigger`
- `lenis`
- `embla-carousel-react`
- `lucide-react`
- `three`
- `@react-three/fiber`
- `@react-three/drei`
- approved Radix packages
- approved shadcn component modules

### Initial shadcn/Radix component surface

- Button
- Card
- Badge
- Separator
- Carousel
- Dialog
- Sheet
- Accordion
- Tabs
- Navigation Menu
- Dropdown Menu
- Tooltip
- Form primitives

### Primary files

- `apps/backend/app/core/static_html_generator.py`
- `apps/backend/app/core/ai_site_generation.py`
- `apps/backend/app/core/compiler_client.py`
- `apps/backend/app/core/sites.py`
- `apps/compiler/src/server.ts`
- `apps/compiler/src/compile.ts`
- `apps/compiler/src/validate.ts`
- `apps/compiler/src/virtual-modules-plugin.ts`
- `apps/compiler/package.json`
- `apps/compiler/fixtures/`

### Acceptance criteria

- `html_v1/v2/v3` still return complete HTML documents.
- An HTML variant can use a compiled GSAP/Lenis bundle.
- An HTML variant can mount a shadcn carousel as a React island.
- An HTML variant can mount a Three.js scene with a 2D fallback.
- All dependency URLs are LenQuant-hosted.
- Undeclared imports fail before publication.
- Every allowed library/component has a compiling fixture.
- The page remains readable and convertible without JavaScript.

## Phase 3: Prevent contradictory and invented briefs

### Goal

Make the master brief evidence-aware and executable.

### Tasks

1. Add a deterministic brief validator before approval.
2. Reject/flag a brief when it requests images but no appropriate approved assets exist.
3. Reject/flag proof sections without approved evidence IDs.
4. Reject specific project locations/descriptions without evidence IDs.
5. Treat missing logo, hero image, gallery images, proof, and footer data as explicit requirements.
6. Remove auto-approval when any hard requirement is unresolved.
7. Populate `missingRequirements` accurately.
8. Add `intentionalFallbacks` for approved typography-only or non-image designs.
9. Generate sections from evidence records, not prose-only summaries.
10. Ensure creative direction respects variant capabilities.
11. Prevent the brief from asking for a custom cursor when the variant policy says default cursor.
12. Prevent the brief from asking for unavailable libraries.

### Generic proof regression assertions

- No testimonial, rating, customer, location, metric, award, or badge is rendered without exact source evidence.
- No proof-like visual treatment may bypass the evidence gate through neutral class names.
- No project caption or location appears without project evidence.
- If project images are cached, the brief uses only their actual labels/locations.
- If source footer data is extracted, the brief includes a proper footer module, not only a CTA bar.

### Primary files

- `apps/backend/app/core/master_brief.py`
- `apps/backend/app/core/extraction_analysis.py`
- `apps/backend/app/core/content_rewriter.py`
- `apps/backend/app/core/creative_copy.py`
- `apps/backend/app/core/sites.py`
- `apps/backend/tests/test_llm_generation_safety.py`
- `apps/backend/tests/test_generation_regressions.py`

### Acceptance criteria

- `missingRequirements` is non-empty when required assets/evidence are missing.
- Auto-approval cannot approve an image-led brief with zero images.
- Auto-approval cannot approve proof without evidence IDs.
- A typography-only fallback is explicit and testable.
- The brief's runtime requests are a subset of the capability manifest.

## Phase 4: Make art direction executable

### Goal

Replace inspirational adjectives with measurable variant requirements while preserving creative freedom.

### Tasks

1. Generate a `VariantDesignContract` before code generation.
2. Require different hero families across the three variants.
3. Require different section rhythms.
4. Require different signature interactions.
5. Bind every image slot to an approved asset role/ID.
6. Bind every proof item to an evidence ID.
7. Declare every SVG's purpose:
   - diagram;
   - icon;
   - brand ornament;
   - visualization;
   - mask/transition;
   - decoration.
8. Reject arbitrary meaningless SVG compositions.
9. Define motion recipes and budgets.
10. Limit each page to one primary signature interaction plus supporting micro-interactions.
11. Disable magnetic/cursor effects by default.
12. Allow magnetic effects only when:
    - fine pointer is available;
    - reduced motion is off;
    - displacement is capped;
    - the default cursor remains visible;
    - the effect stops on blur/leave;
    - touch devices do not run it.

### Suggested variant pattern for home services

This is an example, not a hard-coded template:

#### `html_v1`: Editorial craft

- Real project-photo hero.
- Strong wordmark.
- Quiet GSAP or native reveal choreography.
- Editorial project stories.
- Source-backed credentials/footer.

#### `html_v2`: Immersive process

- Layered image/blueprint treatment.
- GSAP/ScrollTrigger or native sticky storytelling.
- Before/after React island or native control.
- Embla project carousel.
- Optional lightweight Three.js material scene only if justified.

#### `html_v3`: Human/community

- Warm real imagery.
- Tactile transitions.
- No invented testimonials.
- Service area, license, process, and real projects as trust evidence.
- Accessible shadcn/Radix interaction where useful.

### Primary files

- `apps/backend/app/core/variant_strategy.py`
- `apps/backend/app/core/visual_adapter.py`
- `apps/backend/app/core/design_prompts.py`
- `apps/backend/app/core/static_html_generator.py`
- `apps/backend/app/core/ai_site_generation.py`

### Acceptance criteria

- Three variants are materially different beyond palette.
- Every media slot resolves to an approved asset or an explicit fallback.
- Every SVG has a declared purpose.
- Every selected capability is used by the generated bundle.
- No empty media shell can satisfy an image-led contract.
- Magnetic/custom cursor effects are absent unless explicitly selected and safe.

## Phase 5: Add semantic component gates

### Goal

Validate what components do, not merely whether tags or strings exist.

### Hero gate

Require:

- Correct approved logo/wordmark.
- Declared hero mode.
- Approved hero asset for image-led mode.
- Meaningful rendered media area.
- Nonzero image dimensions.
- Appropriate alt text.
- Responsive crop/focal behavior.
- CTA visible and usable.
- No empty geometric “image” panel.

### Footer gate

Require:

- Exactly one distinct `<footer>` after `<main>`.
- Brand identity.
- Current copyright.
- Verified contact action when available.
- Relevant source-backed navigation.
- Verified service area/license when available.
- Privacy/terms links when source-backed or product-required.
- Visual distinction from the final CTA.
- Mobile-readable layout.

Any source-backed footer/contact data is sufficient to require a complete footer.

### Carousel gate

Require:

- Recognized recipe/component ID.
- Two or more items.
- Next/previous controls.
- Current-position state.
- Keyboard support.
- Touch/drag support when declared.
- Focus management.
- Pause on hover/focus for autoplay.
- Reduced-motion behavior.
- Accessible labels.
- Readable non-JS fallback.

### Proof gate

Require evidence IDs for:

- Quotes.
- Ratings.
- Review counts.
- Customer names.
- Project locations.
- Badges.
- Awards.
- Metrics.
- Guarantees.

If evidence is absent, replace proof with source-backed alternatives such as:

- Contractor license.
- Service area.
- Process.
- Real project imagery.
- Years in business if verified.
- Link to a source testimonials page without quoting invented content.

### Gallery gate

Require:

- Approved project asset ID per image card.
- Source-backed caption/location.
- Nonzero rendered media.
- No blank rectangles.
- No fake before/after labels.
- Functional navigation if carousel/horizontal scroll is declared.

### Primary files

- `apps/backend/app/core/static_html_generator.py`
- `apps/backend/app/core/ai_site_generation.py`
- `apps/compiler/src/validate.ts`
- new semantic validator module recommended
- relevant backend/compiler tests

### Acceptance criteria

- Missing `<footer>` is a hard failure.
- Empty hero/project media is a hard failure when media is required.
- Unsupported proof identifies the exact element/evidence failure.
- A carousel cannot pass unless state changes under automated interaction.

## Phase 6: Upgrade runtime and visual QA

### Goal

Test actual user-visible behavior rather than only runtime initialization.

### Runtime QA changes

1. Load the interaction manifest.
2. Execute every required interaction.
3. For each interaction, record:
   - selector;
   - viewport;
   - input method;
   - initial state;
   - final state;
   - accessibility state;
   - console/page errors;
   - screenshot or trace artifact.
4. Test desktop and mobile.
5. Test keyboard-only.
6. Test reduced motion.
7. Test no-WebGL fallback when Three.js is selected.
8. Test no-JS readability.

### Carousel QA

- Click next and confirm active slide/index changes.
- Click previous and confirm reversal.
- Use arrow keys when supported.
- Drag/swipe when declared.
- Confirm controls have accessible names.
- Confirm autoplay pauses on focus/hover.
- Confirm reduced motion disables aggressive autoplay/transitions.

### Animation QA

- Sample computed opacity/transform at multiple timestamps.
- Confirm declared animations actually change state.
- Confirm final content is visible.
- Confirm below-fold elements reveal after scroll.
- Confirm above-fold content is never permanently hidden.
- Confirm reduced motion produces stable visible content.
- Confirm Lenis/GSAP do not break anchor navigation.

### Mobile-menu QA

Fix the current false/real failure modes by checking:

- menu opens;
- menu content becomes visible;
- `aria-expanded` changes;
- focus enters appropriately;
- Escape/close works;
- menu closes;
- page scroll locking is restored;
- desktop nav is not mistaken for mobile nav.

### Visual QA gates

Add deterministic or hybrid checks for:

- Missing footer.
- Empty hero media region.
- Empty project/media rectangles.
- Broken images.
- Duplicate layout signatures.
- Large unexplained blank areas.
- Low contrast.
- Text overflow.
- Mobile horizontal overflow.
- Hidden content after scroll.
- Logo visibility/contrast.

### QA recommendation safety

Before saving an LLM/vision recommendation:

1. Classify whether it requests a proof-bearing fact or asset.
2. Check approved evidence/assets.
3. Rewrite unsafe recommendations to source-safe alternatives.
4. Never recommend invented testimonials, people, ratings, metrics, awards, or client logos.

### Primary files

- `apps/backend/app/core/site_screenshot.py`
- `apps/backend/app/core/screenshot_analyzer.py`
- `apps/backend/app/core/tasks.py`
- `apps/backend/app/core/site_quality_metrics.py`
- `apps/backend/tests/test_screenshot_analyzer.py`
- `apps/backend/tests/test_static_runtime_guards.py`
- `apps/backend/tests/test_quality_score_flow.py`

### Acceptance criteria

- v1-style broken mobile navigation fails with an exact action/assertion.
- v2-style hidden elements fail with exact selectors.
- A dead carousel always fails.
- A missing footer always fails.
- Required animation shows measurable state change.
- Unsafe vision recommendations are blocked or rewritten.
- Runtime readiness cannot be true when required interactions failed.

## Phase 7: Operator preflight and retry UX

### Goal

Expose missing assets, selected capabilities, and intentional fallbacks before a long generation run.

### Preflight UI must show

- Selected primary logo.
- Alternate logo variants.
- Hero asset candidates.
- Project/gallery assets.
- Rejected assets and reasons.
- Proof evidence.
- Missing requirements.
- Runtime mode for each HTML variant.
- Selected libraries/native recipes.
- Estimated bundle/performance risk.
- Intentional fallbacks.
- Whether governed internet imagery is allowed.

### Operator controls

- Approve/reject/re-role an asset.
- Select primary logo/wordmark.
- Select hero image or typography-only mode.
- Enable/disable advanced motion.
- Allow/disallow governed stock search.
- Retry only a failed variant.
- Regenerate after asset correction.
- Preserve successful variants.

### Primary files

- `apps/web/src/components/extraction-review-client.tsx`
- `apps/web/src/components/lead-brief-review.tsx`
- `apps/web/src/components/pipeline-activity-log.tsx`
- `apps/web/src/components/site-review-queue.tsx`
- `apps/web/src/components/lead-variants-view.tsx`
- `apps/backend/app/api/sites.py`
- `apps/backend/app/api/assets.py`

### Acceptance criteria

- An operator can see why no logo/image would be used before generation.
- An image-led brief cannot silently proceed with zero approved images.
- Partial generation presents the exact failed stage and retry action.
- Retrying `html_v3` does not overwrite v1/v2.

## Phase 8: Regression corpus and staged rollout

### Goal

Prevent regressions and measure whether richer HTML actually improves quality.

### Golden corpus

Include at least:

- Home services with strong source imagery.
- Home services with logo but no photography.
- Architecture/portfolio.
- Restaurant/hospitality.
- Clinic/healthcare.
- Creative agency.
- Manufacturing.
- Finance.
- Sites with approved testimonials.
- Sites with testimonial page links but no extracted quotes.
- Sites with no proof.
- Sites with HTTP-only source assets.
- Sites with broken/duplicate images.

### Rollout

1. Run new enhanced HTML variants in shadow mode.
2. Compare against the current vanilla generator.
3. Review:
   - full-run success;
   - asset usage;
   - logo correctness;
   - interaction pass rate;
   - visual approval;
   - performance;
   - latency;
   - cost.
4. Roll out with feature flags:
   - 10%;
   - 25%;
   - 50%;
   - 100%.
5. Automatically roll back on:
   - runtime failure spike;
   - compiler failure spike;
   - excessive latency;
   - performance-budget regression;
   - human visual-approval regression.

### Target metrics

- At least 95% of requested three-variant runs complete all three or return an independently actionable partial result.
- 100% of published proof items have approved evidence IDs.
- 100% of declared required interactions pass automated state-change tests.
- 100% of published pages have a valid footer.
- 100% of published pages pass broken-image and mobile-overflow gates.
- At least 95% of image-led variants use an approved hero asset.
- 100% of image-led variants render non-empty hero media.
- 100% of advanced-motion variants pass reduced-motion checks.
- No Three.js variant publishes without a working fallback.

---

## 8. Detailed test matrix

### Asset tests

- Relative logo URL resolves against page URL.
- HTTP source asset downloads and becomes HTTPS cached render asset.
- Incorrect MIME type is rejected.
- Zero-byte and undecodable image are rejected.
- Tiny favicon does not outrank a full wordmark.
- Duplicate images collapse by checksum.
- Source URL remains provenance and is never rendered directly.
- Disabled downloader produces an explicit blocking state.

### Brief safety tests

- Image-led hero + no hero asset => block.
- Gallery + no project assets => block or explicit non-image fallback.
- Testimonial section + no evidence IDs => remove/block.
- Rating UI + no rating evidence => remove/block.
- Project location + no evidence => remove/block.
- Missing footer data but source has footer => extraction/brief failure.
- Capability requested but unavailable => block before provider call.

### Compiler tests

- Native-only HTML compiles.
- GSAP import compiles and bundles.
- Lenis import compiles and bundles.
- GSAP + Lenis integration fixture compiles.
- React island compiles and mounts.
- shadcn Carousel island compiles and mounts.
- Three.js vanilla scene compiles.
- `@react-three/fiber` island compiles.
- Unsupported package import fails cleanly.
- Generated Tailwind arbitrary utilities appear in CSS.
- Hashed bundle URLs are injected into HTML.
- No external CDN dependency remains.

### Semantic validation tests

- No footer => fail.
- Footer inside main => fail.
- CTA section mislabeled as footer with no footer content => fail.
- Required hero asset outside hero only => fail.
- Empty hero media container => fail.
- Blank project rectangles => fail.
- Evidence-linked quote => pass.
- Unsupported quote with neutral class name => fail.
- Word “review” in a code comment only => no false positive after semantic parser migration.

### Runtime tests

- Mobile menu opens/closes and updates ARIA.
- All reveal elements become visible.
- Carousel click changes active state.
- Carousel keyboard changes active state.
- Carousel drag changes active state when declared.
- Dialog traps/restores focus.
- Accordion updates `aria-expanded`.
- Lenis preserves anchor navigation.
- GSAP cleanup prevents duplicate listeners.
- Three.js fallback runs when WebGL is unavailable.
- Reduced motion disables/simplifies all selected motion.

### Visual tests

- Correct logo visible on light background.
- Correct logo visible on dark background.
- Hero image is non-empty and contextually relevant.
- Gallery images render with stable aspect ratios.
- Footer is distinct and readable.
- No text overflow at 390, 768, 1024, and 1440 widths.
- No horizontal overflow.
- No large empty placeholder panels.
- Three variants are visually distinct.

### Synthetic incident-contract regression fixture

Run synthetic fixtures representing cached source assets, missing media, unsupported proof, footer/contact evidence, selected capabilities, and interaction manifests. Assert that the same generic safety and runtime contracts hold without using an incident site or its data.

---

## 9. Observability requirements

### Asset events

Record:

- discovered count;
- download attempted count;
- download success/failure count;
- promoted count by role;
- rejection reason;
- cache URL generation;
- decode/dimension failures.

### Variant events

Record:

- generator version;
- prompt version;
- capability-manifest version;
- selected capabilities;
- actually bundled dependencies;
- native recipes;
- React islands;
- provider attempts;
- correction attempts;
- validation rule results;
- compilation status;
- upload status;
- runtime QA status;
- visual QA status.

### Interaction QA events

Record:

- interaction ID;
- selector;
- viewport;
- input method;
- initial/final state;
- assertion failure;
- console/page error;
- screenshot/trace reference.

### Quality reporting

Do not collapse everything into one score.

Expose separate gates/scores for:

- Evidence safety.
- Brand fidelity.
- Asset completeness.
- Semantic completeness.
- Interaction reliability.
- Accessibility.
- Performance.
- Visual quality.
- Variant diversity.

A hard-gate failure must not be hidden by a high average score.

---

## 10. Suggested implementation tickets

| ID | Priority | Ticket | Primary area |
|---|---:|---|---|
| GEN-201 | P0 | Persist private rejected artifacts and rule-level failure context | Backend |
| SAFE-202 | P0 | Add evidence-linked proof validation and upstream brief gate | Backend |
| OPS-203 | P0 | Correct “usable” vs generated/validated/runtime-passed terminology | Backend/Web |
| ASSET-204 | P0 | Enable and health-check production asset downloading | Platform |
| ASSET-205 | P0 | Add role-based asset manifest and real logo/hero selection | Extraction |
| BRIEF-206 | P0 | Block contradictory auto-approved briefs | Generation |
| RUNTIME-207 | P1 | Introduce EnhancedHtmlPackage | Backend |
| COMP-208 | P1 | Extend compiler for HTML JS/TS entries and dependency manifests | Compiler |
| COMP-209 | P1 | Add React-island bootstrap support | Compiler/Web runtime |
| COMP-210 | P1 | Expand shadcn/Radix virtual component surface | Compiler |
| COMP-211 | P1 | Add Three.js/R3F/Drei capability and fallbacks | Compiler |
| MOTION-212 | P1 | Add GSAP/Lenis and tested native motion recipes | Compiler/Generation |
| DESIGN-213 | P1 | Implement VariantDesignContract and diversity gate | Generation |
| QA-214 | P1 | Add hero/footer/gallery/proof semantic validators | QA |
| QA-215 | P1 | Add interaction-manifest Playwright runner | QA |
| QA-216 | P1 | Add carousel, motion, React-island, and WebGL fallback tests | QA |
| UI-217 | P2 | Build asset/capability preflight and partial retry UX | Frontend |
| ASSET-218 | P2 | Add governed external image sourcing | Platform/Product |
| ROLL-219 | P2 | Add golden corpus, shadow comparison, rollout flags, dashboards | QA/Platform |

---

## 11. Recommended implementation order

Execute in this order:

1. Phase 0 failure persistence and proof safety.
2. Phase 1 production asset enablement and preflight.
3. Phase 3 brief contradiction/evidence gates.
4. Phase 2 enhanced HTML compiler/runtime.
5. Phase 4 executable art direction.
6. Phase 5 semantic component gates.
7. Phase 6 interaction-aware QA.
8. Phase 7 operator controls.
9. Phase 8 shadow rollout and quality measurement.

Reasoning:

- Modern libraries will not fix missing data or invented content.
- Asset/brief correctness must precede richer rendering.
- Enhanced HTML must precede interaction QA for modern components.
- Semantic and runtime gates must precede broad rollout.

---

## 12. Definition of done for the generic pipeline

The remediation is complete when synthetic fixtures and non-production checks satisfy all of the following:

- [ ] Three requested HTML variants complete, or each failure is independently retryable with exact diagnostics.
- [ ] An approved cached logo/wordmark is used when available.
- [ ] Approved source project imagery is cached and used when selected.
- [ ] Image-led heroes contain a meaningful approved hero image.
- [ ] Typography-only heroes are explicit and contain no fake media placeholder.
- [ ] No empty project/gallery rectangles remain.
- [ ] Every page contains a complete source-backed `<footer>`.
- [ ] No invented testimonial, rating, customer, metric, project claim, or location is published.
- [ ] Any proof content references approved evidence IDs.
- [ ] Any declared carousel passes click, keyboard, and declared drag behavior.
- [ ] Mobile navigation passes.
- [ ] No element remains hidden after scroll.
- [ ] Motion is purposeful and reduced-motion safe.
- [ ] Magnetic/custom cursor behavior is absent unless explicitly justified and gated.
- [ ] HTML remains the principal document.
- [ ] Selected Three.js, GSAP, Lenis, React, and shadcn capabilities are actually compiled and used when appropriate.
- [ ] Native CSS/JS equivalents are accepted when they satisfy the same contract with lower cost.
- [ ] All bundles are same-origin, versioned, and dependency-audited.
- [ ] Runtime QA and visual QA both pass before the site is called usable or publishable.

---

## 13. Instructions to the implementing AI

1. Read this document completely before changing code.
2. Inspect `CLAUDE.md`, repository instructions, and the current git status.
3. Preserve unrelated user changes.
4. Start with Phase 0 and Phase 1; do not jump directly to adding Three.js.
5. Treat production evidence IDs and job IDs in this document as incident references, not fixtures containing secrets.
6. Do not weaken factual-safety validation.
7. Do not hotlink arbitrary source or internet assets.
8. Do not replace the principal HTML path with an opaque full SPA.
9. Build modern capabilities into the HTML packaging/bundling pipeline.
10. Keep semantic content available without JavaScript.
11. Add or update tests with each phase.
12. Run targeted tests after every phase and the full relevant backend/compiler/web suites before completion.
13. Validate generated outputs in a real browser at desktop/mobile sizes.
14. Report exact files changed, tests run, remaining risks, and rollout steps.
15. Do not mark the work complete until the synthetic contract fixtures pass the full definition of done.

## 14. Implementation status and verification boundary (updated 2026-09-03)

### Implemented and test-verified controls

- Generation preflight is fail-closed: discovered source assets with downloading disabled produce an actionable block, and an image-led hero cannot reach a provider without an approved cached HTTPS asset.
- Hero mode is explicit (`image_led` or `typography_only`). Typography-only output rejects fake media shells; image-led output requires approved meaningful media.
- Rendered assets are restricted to approved cached/same-origin assets. The compiler accepts only declared dependencies from its allowlist, bundles them locally, rejects arbitrary/CDN imports, and requires a 2D fallback when Three.js is declared.
- Semantic gates require a footer outside `main` whenever the brief carries footer/contact data, reject unsupported proof-bearing content, and require exact approved evidence IDs for proof markup.
- Runtime QA treats broken assets, failed interaction-manifest actions at desktop/mobile, mobile-menu failures, hidden-after-scroll content, reduced-motion failures, and no-JS unreadability as hard failures. Runtime/visual QA are separate gates and neither may be hidden by an aggregate score.
- Failed provider artifacts are retained only in encrypted short-lived private storage with rule/stage diagnostics. Variant retry targets a single failed variant and preserves successful siblings.
- Preflight exposes selected/rejected/source-only assets, reasons, missing requirements, hero mode/fallback, runtime mode, and actionable blocks. Generation run data records selected capabilities and exact variant failure stage.
- Enhanced rollout uses deterministic feature flags, supports shadow-mode non-publication, and rolls back on configured hard-failure, latency, or performance regression.

### Requires a future production canary

- Validate object-storage permissions, image decoding, cache URLs, and private rejected-artifact retention with real production infrastructure.
- Run the enhanced path in shadow mode against a representative, consented production corpus and compare success, runtime gates, visual approval, latency, performance, and cost before the 10% / 25% / 50% / 100% rollout.
- Exercise real-browser QA against generated production previews, including mobile touch/drag and WebGL-unavailable fallback, before enabling the corresponding capabilities broadly.
- Confirm rollback telemetry is populated with enough samples for its configured thresholds. No production incident rerun is claimed by this document.

### Removed incident-specific requirements

The former Get It Done exact-source regression fixture and its brand names, locations, quotations, assets, and site artifacts are obsolete. They must not be regenerated, preserved, or used as test data. Synthetic fixtures now cover the same generic contracts without retaining incident content.
