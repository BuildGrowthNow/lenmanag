# Phase 11 Implementation Prompt: Operator Workflow and Edit Loop

## Objective

Complete the incomplete items from Phase 11 (Operator Workflow and Edit Loop) as documented in `docs/11-operator-workflow-and-edit-loop.md`. This involves two primary features:

1. **Inline override diffing inside the site workspace** - Add inline diff annotations next to fields that have overrides, showing before/after values directly in the site workspace UI.
2. **Post-export sync guidance surfaced in UI** - Add sync status tracking and guidance to help operators convert local edits back into structured overrides.

## Critical Requirements

### Code Quality Standards
- **NO CODE DUPLICATION**: Do not duplicate existing logic. Reuse existing functions, components, and utilities. If you need similar functionality, extract it into a shared utility.
- **PRODUCTION-READY CODE**: All code must be production-ready with proper error handling, type safety, and edge case handling.
- **FOLLOW EXISTING PATTERNS**: Study the existing codebase patterns (API structure, component organization, error handling) and follow them consistently.
- **PROPER TYPESCRIPT TYPES**: Ensure all frontend code has proper TypeScript types. Do not use `any` unless absolutely necessary.
- **PROPER ERROR HANDLING**: All API calls should have proper error handling with user-friendly error messages.
- **CONSISTENT NAMING**: Use consistent naming conventions across the codebase.

### Backend Requirements
- Use existing Pydantic schemas and extend them rather than creating new ones where possible.
- Follow the existing API endpoint patterns in `apps/backend/app/api/sites.py`.
- Use the existing repository pattern in `apps/backend/app/core/sites.py`.
- Ensure all database operations are properly typed and handle edge cases.
- Add proper logging for debugging and monitoring.

### Frontend Requirements
- Use existing UI components from the component library (shadcn/ui) where possible.
- Follow the existing component patterns in `apps/web/src/components/`.
- Ensure responsive design (mobile-friendly).
- Use proper loading states and error boundaries.
- Follow the existing API client patterns in `apps/web/src/lib/api/`.

## Task 1: Inline Override Diffing Inside Site Workspace

### Backend Changes

**File: `apps/backend/app/core/sites.py`**

1. Add a new method to `SiteRepository`:
   ```python
   def get_override_diff(self, site_id: str) -> list[dict[str, Any]]:
       """
       Returns computed diffs for all active overrides on a site.
       
       For each override, includes:
       - override record (path, scope, value, previousValue, reason)
       - current value in the generated site
       - computed diff showing what changed
       
       Returns a list of diff dictionaries.
       """
   ```

2. The diff computation should:
   - Compare `previousValue` with `currentValue` from the override record
   - Include the current value from the generated site for context
   - Format the diff in a way that's easy to display in the UI (e.g., unified diff format or simple before/after)

3. Modify `get_site()` method to:
   - Call `get_override_diff()` after loading the site
   - Add the computed diffs to the site response (either as a new field or included in the overrides)

**File: `apps/backend/app/schemas/site.py`**

1. Extend `GeneratedSite` schema to include:
   ```python
   overrideDiffs: list[dict[str, Any]] = Field(default_factory=list)
   ```
   Each diff dictionary should contain:
   - `overrideId`: str
   - `path`: str
   - `scope`: str
   - `previousValue`: Any
   - `currentValue`: Any
   - `siteCurrentValue`: Any (the current value in the generated site)
   - `diffType`: str (e.g., "changed", "added", "removed")

### Frontend Changes

**File: `apps/web/src/lib/types.ts`**

1. Update `GeneratedSite` type to include:
   ```typescript
   overrideDiffs: OverrideDiff[];
   ```

2. Add new type:
   ```typescript
   type OverrideDiff = {
     overrideId: string;
     path: string;
     scope: string;
     previousValue: any;
     currentValue: any;
     siteCurrentValue: any;
     diffType: "changed" | "added" | "removed";
   };
   ```

**File: `apps/web/src/components/override-diff-badge.tsx` (NEW FILE)**

Create a new component that:
- Shows a small diff icon badge next to overridden fields
- On hover/click, shows a tooltip with before/after values
- Links to the override record for editing/disabling
- Uses the existing icon library (Lucide)
- Follows the existing badge component patterns

**File: `apps/web/src/app/nsa/sites/[id]/page.tsx`**

1. Add inline diff annotations:
   - In the "Hero variant" card, show diff badge if any hero field has an override
   - In the "Section stack" card, show diff badge for sections with overrides
   - In the "Brand tokens" card, show diff badge for tokens with overrides
   - In the "CTA strategy" card, show diff badge for CTA overrides

2. Add a new card section "Active Overrides" that:
   - Lists all active overrides with their path, scope, and value
   - Shows diff visualization (before → after)
   - Has a disable button that calls the disable override API
   - Uses the existing card component pattern

**File: `apps/web/src/components/site-workspace-controls.tsx`**

1. Add inline diff preview when creating an override:
   - Show the current value of the field being overridden
   - Show a live preview of what the new value will look like
   - Display a diff highlighting the changes
   - Use the existing form patterns

## Task 2: Post-Export Sync Guidance in UI

### Backend Changes

**File: `apps/backend/app/schemas/site.py`**

1. Extend `SiteExportMetadata` schema to include:
   ```python
   exportSyncStatus: Literal["synced", "out_of_sync", "needs_review"] = Field(default="synced")
   lastSyncedAt: datetime | None = Field(default=None)
   ```

**File: `apps/backend/app/core/sites.py`**

1. Add a new method to `SiteRepository`:
   ```python
   def mark_export_out_of_sync(self, site_id: str, export_id: str, reason: str) -> SiteExportMetadata:
       """
       Marks an export as out of sync and records the reason.
       
       Sets exportSyncStatus to "out_of_sync", records a timestamp,
       and adds a note explaining why.
       """
   ```

2. Modify `add_export_metadata()` to initialize `exportSyncStatus` as `"synced"`

3. Add a new method:
   ```python
   def sync_export_edits(self, site_id: str, export_id: str, edits: list[dict[str, Any]]) -> list[SiteOverrideRecord]:
       """
       Converts local edits into structured override records.
       
       Accepts a payload of local edits (path, value pairs),
       converts them into structured override records,
       updates the export's syncStatus back to "synced",
       and returns the created override records.
       """
   ```

**File: `apps/backend/app/api/sites.py`**

1. Add a new endpoint:
   ```python
   @router.post("/{site_id}/export/{export_id}/sync")
   async def sync_export_edits(
       site_id: str,
       export_id: str,
       edits: list[dict[str, Any]],
       session: dict = Depends(_require_session),
   ) -> list[SiteOverrideRecord]:
       """
       Syncs local edits back to structured overrides.
       """
   ```

### Frontend Changes

**File: `apps/web/src/lib/types.ts`**

1. Update `SiteExportMetadata` type to include:
   ```typescript
   exportSyncStatus: "synced" | "out_of_sync" | "needs_review";
   lastSyncedAt: string | null;
   ```

2. Add API client function in `apps/web/src/lib/api/sites.ts`:
   ```typescript
   export async function syncExportEdits(
     siteId: string,
     exportId: string,
     edits: Array<{ path: string; value: any; reason?: string }>
   ): Promise<SiteOverrideRecord[]> {
     // Implementation
   }
   ```

**File: `apps/web/src/components/site-export-controls.tsx`**

1. Add a "Sync Status" indicator showing:
   - Green checkmark for `synced`
   - Yellow warning for `out_of_sync`
   - Blue info for `needs_review`

2. When export status is `out_of_sync`, show a warning banner:
   - "Local edits detected. Sync changes back to structured overrides to preserve them in regeneration."
   - Button to "Sync Local Edits" that opens a modal

**File: `apps/web/src/components/export-sync-modal.tsx` (NEW FILE)**

Create a new component that:
- Shows a list of detected local edits (or manual entry if detection isn't feasible)
- Allows operator to select which edits to sync back
- Converts selected edits to override records via the sync API
- Shows confirmation after successful sync
- Uses the existing modal component patterns

**File: `apps/web/src/app/nsa/sites/[id]/page.tsx`**

1. In the "Export & handoff" card:
   - Show sync status prominently
   - Add a reminder note: "After making local edits, sync them back to preserve them in future regenerations."
   - Add a "Sync Edits" button when status is `out_of_sync`

## Implementation Order

1. Start with Task 1 (Inline Override Diffing):
   - Backend: Add diff computation method and schema updates
   - Frontend: Create diff badge component and add inline annotations
   - Test with existing override records

2. Then Task 2 (Post-Export Sync Guidance):
   - Backend: Add sync status tracking and sync endpoint
   - Frontend: Create sync modal and add sync status indicators
   - Test with export workflows

## Testing & Verification

- Write unit tests for new backend methods (`get_override_diff`, `mark_export_out_of_sync`, `sync_export_edits`)
- Test the inline diff UI with various override scenarios (text changes, array changes, nested object changes)
- Test the sync workflow: export → mark out of sync → sync back → verify overrides created
- Ensure all error cases are handled (invalid paths, missing fields, permission errors)
- Verify the UI is responsive and works on mobile devices

## What Already Exists

- `SiteOverrideRecord` schema stores `previousValue` and `currentValue`
- `GeneratedSite.overrides` field contains all override records
- `SiteWorkspaceControls` component has override creation form
- Separate compare view exists at `/nsa/sites/[id]/compare/page.tsx`
- `SiteExportMetadata` schema exists with `exportType`, `repoUrl`, `branch`, `commitSha`
- Export history is tracked in `site_exports` collection
- Export controls component exists with export form

## Final Notes

- Do not modify the existing compare view - this is about inline diffing in the main workspace
- The sync detection for local edits may need to be manual entry if automatic detection isn't feasible (Git diff analysis would be complex)
- Ensure all new components follow the existing design system (colors, spacing, typography)
- Add proper loading states for async operations
- Handle edge cases like deleted exports, disabled overrides, and concurrent edits
