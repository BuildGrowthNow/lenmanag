# Operator Workflow and Edit Loop

## Purpose

Define how a single operator uses the system before and after a meeting to improve a lead's website, keep changes safe, and export or hand off work without losing traceability.

This doc is the practical bridge between generation and real-world editing.

## Core Principle

The rendered preview is not the source of truth.

The source of truth is:

1. the lead record
2. the extracted site brief
3. the generated site spec
4. approved override records
5. export metadata and snapshots

Any local or GitHub copy is a derivative artifact of that source of truth.

## Operator Workflow

Recommended loop:

1. capture or import the lead
2. generate a brief from public source material
3. generate the first preview
4. review the preview locally or in the browser
5. apply changes as structured overrides
6. regenerate from the same brief plus overrides
7. compare the new preview against the previous version
8. export or share the finished result

This loop should support both:

- pre-call refinement, where the goal is to show a stronger site in the meeting
- post-call refinement, where the goal is to update the preview after feedback

## What Can Be Edited

Edits should be structured, not ad hoc.

Supported override categories should include:

- copy
- layout
- CTA
- brand treatment
- motion
- styling
- section order
- proof emphasis

Each override should store:

- the field or path being changed
- the previous value
- the new value
- the reason for the change
- who made the change
- when the change was made
- whether the change has been approved for regeneration

## Source of Truth Rules

- Do not treat rendered HTML as canonical.
- Do not overwrite generated site records directly when a manual edit is made.
- Do not lose prior generated values when adding overrides.
- Do keep the original generated version available for diff and rollback.
- Do keep export bundles marked as snapshots, not canonical state.

## Regeneration Rules

Regeneration should work like a merge:

1. load the original generated site spec
2. load approved overrides
3. merge them into the render payload
4. preserve any unresolved gaps or QA blockers
5. render a new preview version
6. keep the previous version intact for comparison

If a regenerated output conflicts with a hard quality rule, the system should block the change and surface the conflict to the operator.

## Local Editing Modes

The system should support two practical editing modes.

### Mode 1: Structured Edit Mode

This is the preferred mode.

- operator edits happen in the admin UI
- the system stores overrides
- regeneration is deterministic
- version history remains clean

### Mode 2: Exported Snapshot Mode

This is for cases where you want to work with actual code locally or in GitHub.

- the system exports a site snapshot or bundle
- the snapshot can be opened locally or pushed to a repo
- changes made in the snapshot are treated as a derivative working copy
- important changes should be converted back into overrides or exported as a new snapshot reference

The exported snapshot should never be confused with the canonical site spec.

## GitHub and Local Hand-off

If the operator wants code available locally or in GitHub, the system should support:

- exporting a site snapshot to a local folder
- exporting a site snapshot to a GitHub repo
- storing branch and commit references
- marking the snapshot as current, stale, or superseded
- recording the relationship between the exported code and the source lead

Recommended handling:

- use the exported snapshot for direct code work when needed
- sync the important changes back into override records or a new generated version
- keep the canonical lead/spec/override data in the main system

## Recommended File Boundaries

If the snapshot is exported as code, it should roughly separate into:

- shared renderer and theme code
- lead-specific content data
- lead-specific override data
- asset references
- preview/runtime metadata

Avoid embedding one-off business logic directly into generated page files unless it is intentionally part of the override layer.

## Review Checklist

Before a site is sent or shown in a meeting, verify:

- the preview matches the source brand direction
- the hero is strong enough to sell the call
- mobile layout still reads cleanly
- CTA copy matches the intended next step
- no placeholder content remains
- all operator edits are visible in the diff
- export status is current if a handoff bundle exists
- the preview can be explained back to the client in plain language

## Export Outcomes

An export should explicitly state one of these outcomes:

- preview only
- local working copy
- GitHub snapshot
- handoff bundle
- client-ready version

That makes it obvious whether the exported code is meant for internal iteration or final delivery.
