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

## Implementation status

**Checklist**

- [x] Structured override APIs + UI for copy/layout/theme edits with regeneration hooks (`app/api/sites.py#create_override`, `apps/web/src/components/site-workspace-controls.tsx`).
- [x] Version history + compare view so operators can diff regenerated previews before/after overrides (`/api/sites/{id}/versions`, `apps/web/src/app/nsa/sites/[id]/compare/page.tsx`).
- [ ] Inline override diffing inside the site workspace (current compare view is separate; inline annotations still pending).
  - **Backend changes needed:**
    - File: `apps/backend/app/core/sites.py`
    - Add a new method to `SiteRepository`:
      - `get_override_diff(site_id: str) -> list[dict[str, Any]]` that returns:
        - All active overrides for the site
        - For each override, include: current value, previous value, path, scope, and the field's current value in the generated site
        - A computed diff showing what changed (e.g., unified diff format or before/after comparison)
    - Extend `GeneratedSite` schema in `apps/backend/app/schemas/site.py` to include:
      - `activeOverrides: list[SiteOverrideRecord]` - pre-filtered to only active overrides
      - `overrideDiffs: list[dict[str, Any]]` - computed diff for each override
    - Modify `get_site()` to populate these fields by calling the new diff method
  - **Frontend changes needed:**
    - File: `apps/web/src/app/nsa/sites/[id]/page.tsx`
    - Add inline diff annotations next to fields that have overrides:
      - In the "Hero variant" card, show diff badge if `hero.headline` has an override
      - In the "Section stack" card, show diff badge for sections with overrides
      - In the "Brand tokens" card, show diff badge for tokens with overrides
      - In the "CTA strategy" card, show diff badge for CTA overrides
    - Create a new component `apps/web/src/components/override-diff-badge.tsx` that:
      - Shows a small diff icon badge next to overridden fields
      - On hover/click, shows a tooltip with before/after values
      - Links to the override record for editing/disabling
    - Add a new card section "Active Overrides" that lists all overrides with:
      - Path, scope, and value
      - Diff visualization (before → after)
      - Disable button calling the disable override API
    - File: `apps/web/src/components/site-workspace-controls.tsx`
    - Add inline diff preview when creating an override:
      - Show the current value of the field being overridden
      - Show a live preview of what the new value will look like
      - Display a diff highlighting the changes
  - **What already exists:**
    - `SiteOverrideRecord` schema stores previousValue and currentValue
    - `GeneratedSite.overrides` field contains all override records
    - `SiteWorkspaceControls` component has override creation form
    - Separate compare view exists at `/nsa/sites/[id]/compare/page.tsx`
  - **What needs to be done:**
    - Add backend diff computation logic
    - Extend site schema with override diff fields
    - Build inline diff badge component
    - Add inline diff annotations throughout the site workspace
    - Add live diff preview in override creation form
    - Create dedicated "Active Overrides" card

- [x] Export + bundle recording with commit metadata for local/GitHub handoff (`app/api/sites.py#recordSiteExport`, `apps/web/src/components/site-export-card.tsx`).
- [ ] Post-export sync guidance surfaced in UI (documentation describes workflow but UI lacks reminders to convert local edits back into structured overrides).
  - **Backend changes needed:**
    - File: `apps/backend/app/core/sites.py`
    - Add a new field `exportSyncStatus: str` to `SiteExportMetadata` schema with values: `synced`, `out_of_sync`, `needs_review`
    - Add a new field `lastSyncedAt: datetime | None` to track when local edits were last synced back
    - Add a new method `mark_export_out_of_sync(site_id: str, export_id: str)` that:
      - Sets the export's syncStatus to `out_of_sync`
      - Records a timestamp
      - Adds a note explaining why (e.g., "Local edits detected after export")
    - Modify `add_export_metadata()` to initialize syncStatus as `synced`
    - Add a new endpoint `POST /api/sites/{site_id}/export/{export_id}/sync` that:
      - Accepts a payload of local edits (path, value pairs)
      - Converts them into structured override records
      - Updates the export's syncStatus back to `synced`
      - Returns the created override records
  - **Frontend changes needed:**
    - File: `apps/web/src/components/site-export-controls.tsx`
    - Add a "Sync Status" indicator showing:
      - Green checkmark for `synced`
      - Yellow warning for `out_of_sync`
      - Blue info for `needs_review`
    - When export status is `out_of_sync`, show a warning banner:
      - "Local edits detected. Sync changes back to structured overrides to preserve them in regeneration."
      - Button to "Sync Local Edits" that opens a modal
    - Create a new component `apps/web/src/components/export-sync-modal.tsx` that:
      - Shows a list of detected local edits (if we can detect them, or manual entry)
      - Allows operator to select which edits to sync back
      - Converts selected edits to override records via the sync API
      - Shows confirmation after successful sync
    - File: `apps/web/src/app/nsa/sites/[id]/page.tsx`
    - In the "Export & handoff" card, show sync status prominently
    - Add a reminder note: "After making local edits, sync them back to preserve them in future regenerations."
    - Add a "Sync Edits" button when status is `out_of_sync`
  - **What already exists:**
    - `SiteExportMetadata` schema exists with exportType, repoUrl, branch, commitSha
    - Export history is tracked in `site_exports` collection
    - Export controls component exists with export form
  - **What needs to be done:**
    - Add sync status tracking to export metadata
    - Create sync endpoint to convert local edits to overrides
    - Build sync status indicator in export controls
    - Create sync modal for converting local edits
    - Add guidance reminders in the site workspace
    - Implement detection of local edits (if feasible) or manual entry
  - **Implementation status:**
    - ✅ COMPLETED - Phase 11 implementation completed successfully
    - ✅ Backend: Added `get_override_diff()` method to SiteRepository
    - ✅ Backend: Extended GeneratedSite schema with overrideDiffs field
    - ✅ Backend: Modified get_site() to populate override diffs
    - ✅ Backend: Extended SiteExportMetadata schema with exportSyncStatus and lastSyncedAt fields
    - ✅ Backend: Added mark_export_out_of_sync() method
    - ✅ Backend: Added sync_export_edits() method
    - ✅ Backend: Added /api/sites/{id}/export/{export_id}/sync endpoint
    - ✅ Frontend: Added OverrideDiff type to types.ts
    - ✅ Frontend: Created override-diff-badge.tsx component
    - ✅ Frontend: Added inline diff annotations in site workspace page
    - ✅ Frontend: Added Active Overrides card section
    - ✅ Frontend: Added diff preview in site-workspace-controls
    - ✅ Frontend: Updated SiteExportMetadata type with sync status fields
    - ✅ Frontend: Added syncExportEdits() API function
    - ✅ Frontend: Added sync status indicator in export controls
    - ✅ Frontend: Created export-sync-modal.tsx component
    - ✅ Frontend: Integrated sync guidance with "Sync Local Edits" button in export controls
