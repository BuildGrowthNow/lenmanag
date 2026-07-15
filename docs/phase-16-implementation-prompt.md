# Phase 16 Implementation Prompt: Operator-Driven Redesign and Regeneration

## Overview

Phase 16 focuses on operator-directed refinement: giving the admin a safe prompt workflow to regenerate previews, improve the design, and produce a new premium result based on explicit operator guidance.

## Context

This phase follows Phase 15, which makes the preview delivery production-ready. Phase 16 adds the operator feedback loop so the system can respond to direction, refine the design, and persist prompt-driven preview versions.

## Status: ✅ Complete

> Current codebase already includes a backend regeneration entrypoint (`POST /api/sites/{site_id}/regenerate`) and versioned preview storage, but it lacks an admin prompt input workflow and the `refinementPrompt`/prompt history model needed for operator-directed redesigns.

## Goal

- Enable operators to provide natural-language refinement prompts in the admin.
- Regenerate the redesign using the current site data, previous preview state, and operator prompt.
- Store prompt history and preview version metadata for traceability.
- Ensure the regeneration workflow is safe, repeatable, and does not produce placeholder or broken previews.

## Deliverables

- Admin UI panel for submitting redesign refinement prompts.
- Backend endpoint to accept prompt refinements and trigger a new redesign generation.
- Safe regeneration workflow that preserves approved brand tokens and site content.
- Extend the existing regenerate endpoint rather than duplicating regenerate job logic.
- Versioned preview output with metadata linking the prompt, operator, and design iteration.
- Prompt history visible in the admin preview workspace.
- Preview quality guardrails that block low-quality reruns.
- Public preview update flow that replaces the previous preview only after the new redesign passes QA.

## Exit criteria

- Operators can submit a redesign prompt and receive a regenerated preview.
- Prompt inputs are persisted with the resulting preview version.
- The admin surface shows prompt history, current preview status, and whether the redesign passed or needs additional refinement.
- The generation pipeline can safely rerun without losing previously approved source references.
- The system maintains production readiness for frontend/backend after regeneration.

## Implementation tasks

- Add a `refinementPrompt` field and prompt history model to the preview generation schema.
- Add backend support for `POST /api/sites/{id}/regenerate` or similar endpoint.
- Extend the existing regenerate endpoint to accept prompt guidance and preserve version history.
- Add admin UI controls in the site preview workspace for prompt submission and status monitoring.
- Implement a generation adapter that combines existing extraction/brief data with the operator prompt.
- Add traceability so each prompt-driven generation is linked to the site, brief, and operator.
- Add guardrail logic to avoid placeholder, generic, or off-brand preview outputs.
- Add UI feedback for in-progress regeneration, successful preview update, and failure reasons.
- Add tests for prompt-driven regeneration and prompt history persistence.

### Operator refinement prompt model
- `refinementPrompt`: string, optional
- `promptHistory`: array of { `promptId`, `submittedAt`, `operatorId`, `promptText`, `resultVersionId`, `status`, `qualityScore` }
- `promptStatus`: `pending` | `success` | `failed`

### Regeneration endpoint contract
- Request: `POST /api/sites/{site_id}/regenerate`
  - body: `{ "refinementPrompt": string, "force": boolean? }`
- Response: `{ "siteId": string, "previewVersionId": string, "qualityScore": number, "status": "queued" | "completed" | "failed" }

### Admin prompt examples
- "Make this page feel more premium and trust-driven while keeping the core product narrative intact."
- "Use stronger visual hierarchy and simplify the hero section to prioritize the main CTA."
- "Keep the brand colors and imagery but make the layout feel more modern and editorial."

### Safety and guardrails
- Only use the operator prompt to refine layout, tone, and section choice; do not rewrite extracted product facts or invent new capabilities.
- If the prompt is vague, ask for a more specific refinement rather than regenerating blindly.
- Block prompts that request fake testimonials, unsupported claims, or speculative pricing.
- Persist the original prompt and the resulting preview version for traceability.

## Testing requirements

- Test endpoint validation for operator prompts.
- Test that regenerated previews respect current site and brief data.
- Test prompt history persistence and admin display.
- Test that low-quality or invalid prompt reruns are rejected with clear admin messages.
- Test that public preview replacement occurs only after QA success.

## Success criteria

- Operator prompt-driven design regeneration works end to end.
- The admin can iterate on preview quality from within the workspace.
- Regenerated previews remain production-ready and traceable.
- The system supports repeated refinements without manual code changes.
