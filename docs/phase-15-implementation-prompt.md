# Phase 15 Implementation Prompt: Premium Preview Delivery and Refinement

## Overview

Phase 15 focuses on making the generated preview production-ready by turning extracted site data into a premium, unique redesign and validating it with screenshot-based QA.

## Context

This phase builds on the extraction, brief, and preview generation work from earlier phases. The goal is to close the gap between a working preview generator and a production-quality redesign engine that delivers branded, high-end layouts and verifies them with a screenshot review loop.

## Status: ❌ Not started

> Current codebase already includes partial infrastructure for this phase: `visualRedesign` schema support, `generate_visual_redesign_brief` integration, component-driven preview rendering, preview metadata fields, a public preview URL model, and placeholder screenshot metadata storage. What remains is the real screenshot capture + Gemini vision QA loop and tying quality results to preview completion.

## Goal

- Deliver a preview generation pipeline that consistently produces premium, bespoke redesigns for every site.
- Ensure the preview renderer respects AI-recommended component assignments and design treatments.
- Add screenshot QA and refinement so previews are evaluated and improved before they are surfaced to operators.

## Deliverables

- Backend preview generation uses `visualRedesign` component mappings to build structured page sections.
- Frontend preview renderer in `apps/web/src/app/sites/[slug]/page.tsx` uses `section.componentId` for premium components.
- A library of premium section components that support:
  - editorial hero treatment
  - dynamic bento/service grids
  - testimonial/carousel proof layouts
  - masonry work/gallery presentations
  - process timeline and brand statement sections
  - conversion-focused CTA panels
- Screenshot capture of generated preview pages.
- Automated QA analysis of the screenshot against premium design heuristics.
- Public preview URLs that can be shared and are visible in the admin.
- Validate and replace the current placeholder screenshot/quality logic with a real Gemini vision evaluation loop.
- Backend and frontend linkages for preview metadata, generation status, and quality score.

## Exit criteria

- Every generated preview uses component-driven layouts when `componentId` is present.
- The preview page is production-ready and visually distinct per site.
- The system captures a full-page screenshot of the generated preview.
- The screenshot is analyzed and returns a quality evaluation before the preview is marked complete.
- The admin surface shows preview generation state, quality score, and the shareable preview URL.
- Frontend and backend implementation are stable enough for a staging deployment.

## Implementation tasks

- Update the preview renderer to prefer `section.componentId` and map IDs to high-end Tailwind/ShadCN components.
- Build a premium section component library in the preview renderer layer.
- Ensure generated copy and visual treatment derive from the extracted site brand and content, not internal instruction text.
- Add backend preview metadata for screenshot capture status and visual QA results.
- Integrate a screenshot capture utility into the preview generation pipeline.
- Add a screenshot QA analyzer to score preview pages and flag sections that need improvement.
- Replace placeholder layout hash comparison logic with an actual visual QA implementation.
- Surface preview quality and screenshot status in the admin site workspace.
- Harden the preview build so it can be deployed and run in production through the existing FastAPI/Next.js stack.

### AI Handoff Prompt (for Phase 15 automation)

When handing Phase 15 to an LLM/agent (Gemini), provide the following instruction block and inputs. The agent must output strictly-typed JSON matching `VisualRedesignBrief[]` and, if an iteration is required, a single improved `VisualRedesignBrief[]` iteration.

Inputs provided to the agent:
- `extraction`: the consolidated `ExtractionSnapshot` (sectionInventory, pageInventory, assetUrls, images)
- `brief`: the approved `SiteBrief` with `toneProfile` and `recommendedSections`
- `brandTokens`: extracted `BrandTokens` (paletteMode, primary/secondary/accent colors, typography, imageStyle, motion)
- `availableComponents`: list of premium component ids and descriptions (see `VisualRedesignAnalyzer.AVAILABLE_COMPONENTS`)
- `qualityThreshold`: integer (0-100), target quality (e.g., 95)
- `screenshotExamples`: optional URLs/images used as style references (Awwwards-inspired)

Agent task (strict):
1. Analyze up to 10 extracted sections and recommend a `recommendedComponent` for each, plus `visualDirection`, `contentToReuse` and `contentToRewrite` arrays.
2. Emit `VisualRedesignBrief[]` JSON only. Each `VisualCritique` must include a valid `recommendedComponent` id.
3. If a separate screenshot QA call yields `qualityScore < qualityThreshold`, produce one improved `VisualRedesignBrief[]` output that targets the low-scoring sections and explains changes (still JSON-only).

Required JSON schema (output):
```
[
  {
    "pageUrl": "string",
    "artDirection": "string",
    "critiques": [
      {
        "sectionType": "string",
        "originalStrengths": ["string"],
        "originalWeaknesses": ["string"],
        "redesignGoal": "string",
        "contentToReuse": ["string"],
        "contentToRewrite": ["string"],
        "recommendedComponent": "component-id",
        "visualDirection": "string",
        "confidence": 0
      }
    ]
  }
]
```

Operational notes:
- Use Tailwind + ShadCN component patterns; provide component mapping keys (IDs) rather than raw HTML.
- Keep copy rewrites grounded in source content; do not invent testimonials, metrics, pricing, or facts not present in the extracted site.
- Prefer a `recommendedComponent` that matches the section intent: hero, services, proof, gallery, timeline, CTA, or editorial feature.
- If `confidence < 50` for many sections, mark them for operator review rather than auto-publish.
- After producing JSON, call the screenshot capture service (Playwright), capture a full-page screenshot, and call the Gemini Vision QA prompt to score sections and overall quality.
- If `qualityScore < qualityThreshold`, re-run the above (single improved pass) and return the improved JSON and new score.

### Screenshot QA contract
- Required output from the analyzer:
  - `desktopScreenshotUrl`: public URL or storage reference
  - `mobileScreenshotUrl`: public URL or storage reference
  - `layoutHash`: stable hash for this render
  - `qualityScore`: integer 0-100
  - `sectionScores`: array of { `sectionId`, `score`, `critique`, `recommendation` }
  - `rawCritique`: full Gemini response text for traceability

### Gemini prompt templates
#### Visual redesign generation prompt
Use a JSON-friendly prompt such as:
```text
You are an assistant that converts extracted site content and brand signals into a premium website redesign brief. Output only valid JSON matching the `VisualRedesignBrief[]` schema. Use `availableComponents` IDs and select the best component for each section. Keep copy rewrites grounded in source content and avoid invented testimonials, pricing, or metrics.
```

#### Screenshot QA prompt
Use a JSON-friendly prompt such as:
```text
You are a visual QA assistant reviewing a rendered website screenshot. Score overall quality 0-100 and assign each extracted section a score with a short critique. Use design heuristics: hierarchy, spacing, contrast, image treatment, readability, and conversion clarity. Return a JSON object with `qualityScore`, `sectionScores`, and `rawCritique`.
```

#### Improvement prompt (single pass)
Use a JSON-friendly prompt such as:
```text
The previous redesign scored below threshold. Improve the existing `VisualRedesignBrief[]` by addressing low-scoring sections and increasing visual polish. Return only a new `VisualRedesignBrief[]` JSON. Keep brand tokens and core site messages intact.
```

This block should allow an autonomous agent to complete Phase 15 by: (1) generating `visualRedesign` briefs, (2) mapping to `componentId`s, (3) triggering capture+QA, and (4) optionally producing a single improved iteration when below threshold.

## Testing requirements

- Validate preview rendering for each supported `componentId`.
- Validate fallback behavior for sections without `componentId`.
- Validate screenshot capture works for rendered public preview URLs.
- Validate QA analyzer produces a score and updates preview metadata.
- End-to-end test that a generated preview appears in admin and returns a shareable URL.

## Success criteria

- A generated preview is stable and visually premium enough for operator review.
- The preview pipeline is production ready from backend generation through frontend render.
- Screenshot QA prevents low-quality previews from being released.
- The system generates previews that are clearly different and tailored to each client site.
