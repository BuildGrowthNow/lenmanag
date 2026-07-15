# Phase 17 Implementation Prompt: Deep Crawl, Batch Redesign, and Operator Handoff

## Overview

Phase 17 finalizes the pipeline so that the admin can submit a single canonical URL for a target site, the system uses the existing deep crawl pipeline (homepage + sitemap + internal links within budget) to extract brand and content across multiple pages, generates a premium, unique redesign per lead using Gemini (text + vision), captures screenshots, evaluates visual quality against premium heuristics (Awwwards-inspired), auto-improves a single time if below threshold, and exposes a robust operator-driven refinement workflow. Completion of Phase 15 and Phase 16 plus this phase achieves the user's objective.

## Status: ❌ Not started

## Goal

- Accept a single canonical URL in the admin (existing lead/website input) and rely on the existing crawler to traverse homepage, sitemap, and key internal links within crawl budgets.
- Extract brand tokens, images, copy candidates, page sections, CTAs, objectives and visual cues across the discovered pages.
- Generate a premium visual redesign brief using Gemini (text + vision) that recommends `componentId`s and art direction per section.
- Render the preview using premium Tailwind / ShadCN components, capture a full-page screenshot, and evaluate quality using a Gemini Vision QA analyzer.
- If the quality score is below the configured threshold, call Gemini to produce a single improved redesign iteration and re-run capture/QA.
- Persist preview versions and prompt history; allow operators to submit refinement prompts which trigger safe, traceable regeneration.

## Deliverables

- Reuse the existing single-URL lead/website input; no new multi-URL admin surface. Confirm the current `crawl_website` implementation follows sitemap and internal links and that the resulting `ExtractionSnapshot` contains a rich `sectionInventory`, `brandAssetCues`, `sourceCitations`, and `pageInventory` for redesign.
- `Phase 15` tasks implemented: screenshot capture + Gemini Vision QA + automatic single iteration improvement.
- `Phase 16` tasks implemented: `refinementPrompt` field, prompt history model, admin prompt UI, and regenerate adapter that consumes operator prompts.
- `ScreenshotAnalyzer` implementation that uses Gemini Vision (or equivalent) for section-by-section quality scoring and an overall `qualityScore` (0-100).
- Admin surface shows preview generation state, quality score, screenshots, prompt history, and shareable public preview URL.

## Exit criteria

- Admin can input a single URL for a lead (existing flow), and the crawler reliably discovers and crawls multiple pages (within configured budgets) for that site.
- Every preview generation uses `componentId` when present and maps to premium components in the renderer.
- The pipeline captures full-page screenshots and stores `SiteScreenshotMetadata` and `screenshotRefs`.
- Visual QA returns a numeric `qualityScore` and either completes or triggers one automatic improvement pass.
- Operator can submit a `refinementPrompt` that is persisted and used to regenerate a new version; prompt history is visible.
- The public preview is only replaced after QA success.

## Implementation tasks

1. Backend: deep crawl from a single seed URL
   - Keep the existing single-URL website input (`lead.websiteUrl`) as the only operator-facing control.
   - Verify and, if needed, refine `crawl_website` so it:
     - Normalizes the canonical URL.
     - Attempts sitemap discovery.
     - Follows internal links within `crawl_max_pages`, `crawl_budget_bytes`, and `crawl_time_limit_seconds`.
   - Ensure the resulting `ExtractionSnapshot` for a lead contains a meaningful `sectionInventory`, `brandAssetCues`, `sourceCitations`, and `pageInventory` drawn from the crawled pages.

2. Backend: screenshot capture + Gemini Vision QA
   - Implement `apps/backend/app/core/screenshot_analyzer.py` using Playwright for capture and Gemini Vision for evaluation.
   - Replace `ScreenshotComparator.compare_layout_screenshot` placeholder with real capture/compare operations.
   - Add `visual_redesign_max_iterations` and `visual_redesign_quality_threshold` usage to control iteration.

3. Backend: single automatic improvement pass
   - When `qualityScore < threshold`, compose a Gemini prompt that asks for a targeted improvement of the VisualRedesignBrief and recommended components, then re-run the renderer and capture once more.
   - Limit to one auto-iteration.

4. Backend: prompt history & refinementPrompt
   - Rely on Phase 16 for `RefinementPromptRecord`, `refinementPromptId`, and `promptHistory` on `GeneratedSite`/`GeneratedSiteVersion`.
   - Ensure the auto-improvement loop and deep crawl enhancements do not break prompt history linkage and that regenerated versions remain traceable back to operator prompts.

5. Frontend: admin UI
   - Keep the existing lead/extraction UI that accepts a single `websiteUrl` per lead; do not add multi-URL input.
   - Ensure the site workspace (`apps/web/src/app/nsa/sites/[id]/page.tsx`) clearly surfaces:
     - Current quality score and QA status.
     - Screenshot previews.
     - Prompt history and the current `refinementPromptId` (from Phase 16 components).

6. Frontend: renderer components
   - Ensure `apps/web/src/app/sites/[slug]/page.tsx` chooses `section.componentId` when present and falls back gracefully.
   - Add or confirm presence of premium components in `apps/web/src/components/premium/` and update `component-registry.ts`.

7. Tests & automation
   - Add unit tests for the `ScreenshotAnalyzer` and integration tests for the auto-improvement loop.
   - Update `apps/web` Playwright tests to assert screenshot capture and quality score display.

## Testing requirements

- Crawl acceptance test for single-URL input producing non-empty `sectionInventory` and reasonable `pagesDiscovered` / `pagesCrawled` counts.
- VisualRedesignBrief tests verifying recommended components are valid.
- Screenshot capture tests (Playwright) that store `desktopScreenshotUrl` and `mobileScreenshotUrl`.
- QA loop tests to assert that a low-quality design triggers one auto-improvement attempt and updates `qualityScore`.
- Regenerate endpoint tests ensuring `refinementPrompt` is stored in `promptHistory` and used in generation.

## Approximate timeline

- Backend multi-URL crawl + extraction merge: 1–2 days
- Screenshot analyzer + Gemini Vision evaluation: 2–4 days
- Auto-improvement loop: 1–2 days
- Prompt history + regenerate adapter: 1 day
- Frontend admin UI + prompt input: 1–2 days
- Tests and polishing: 1–2 days

## Notes and constraints

- Gemini Vision use requires API credentials and cost estimation; fallback path should exist for on-prem Playwright + heuristic scoring.
- Playwright must be added to `pyproject.toml` and runtime environment for background capture.
- Limit automatic improvements to one pass to avoid runaway costs.

### AI Handoff Prompt (for Phase 17 automation)

When handing Phase 17 to an LLM/agent, include this task and the same contract used for Phase 15 and Phase 16, but emphasize **single-URL input with deep crawl** (homepage + sitemap + internal links) rather than multi-URL admin controls.

Inputs:
- `seedUrl`: the canonical site URL for the lead
- `extraction`: `ExtractionSnapshot` produced from the deep crawl of that URL
- `siteBrief`: approved `SiteBrief` with extracted brand tokens and recommended sections
- `availableComponents`: list of valid premium component IDs
- `qualityThreshold`: integer
- `visualRedesignMaxIterations`: integer
- `priorPromptHistory`: optional prompt history for existing site

Task:
1. Deep-crawl the single `seedUrl` using the existing crawler (homepage + sitemap + internal links within budgets) to build a rich `ExtractionSnapshot`.
2. Generate a premium `VisualRedesignBrief[]` JSON using `availableComponents`.
3. Render the preview and capture screenshots for desktop and mobile.
4. Run the Gemini Vision QA prompt and compute `qualityScore`.
5. If below threshold, perform one single improvement iteration and recapture.
6. Persist `screenshotRefs`, `qualityScore`, `layoutHash`, `promptHistory`, and version metadata.

Expected output:
- `siteId`
- `previewVersionId`
- `qualityScore`
- `screenshotRefs`
- `layoutHash`
-- `promptHistory`
-- `crawlUrls` (the list of URLs actually crawled for this site)

### Deep crawl details
- Accept a single `seedUrl` per lead and let the crawler traverse homepage, sitemap entries, and internal links for that domain.
- Enforce budgets: `crawl_max_pages`, `crawl_budget_bytes`, `crawl_time_limit_seconds`.
- Deduplicate extracted sections, assets, and images across pages.
- Treat the crawl as a single site briefing input for the redesign engine.

---

Phase 14–16 + this Phase 17 together implement your objective end-to-end when the missing pieces (screenshot capture, vision QA, prompt history + admin UI) are completed.