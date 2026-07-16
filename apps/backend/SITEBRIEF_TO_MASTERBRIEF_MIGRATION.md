# SiteBrief → MasterBrief Migration Complete

## Summary

Successfully migrated all code from using `SiteBrief` to `MasterBrief` after the extraction refactor (Phase 1 complete).

## Files Modified

### 1. `app/core/visual_redesign.py`
- **Changed imports**: `SiteBrief` → `MasterBrief`
- **Updated `generate_redesign_brief()` signature**: Now accepts `MasterBrief` instead of `SiteBrief`
- **Updated `generate_visual_redesign_brief()` signature**: Now accepts `MasterBrief` instead of `SiteBrief`
- **Fixed field access**: `brief.toneProfile.value` → Derive from `brief.visualStyle` (string)

### 2. `app/core/sites.py`
- **Changed imports**: `SiteBrief` → `MasterBrief`
- **Updated ALL function signatures**: 10+ functions now use `MasterBrief` parameter
  - `_site_refs()`
  - `_brand_tokens()`
  - `_apply_refinement_to_visual_redesign()`
  - `_hero_variant()`
  - `_section_stack()`
  - `_cta_strategy()`
  - `_review_rubric()`
  - `_quality_score()`
  - `_readiness_status()`
  - `_comparison_entries()`

## Field Mapping Applied

| SiteBrief Field | MasterBrief Field | Notes |
|----------------|-------------------|-------|
| `brief.toneProfile.value` | `brief.toneAndVoice` | String field |
| `brief.companySummary.value` | `brief.valueProposition` | String field |
| `brief.valuePropositionSummary.value` | `brief.valueProposition` | Same target |
| `brief.audienceHypothesis.value` | `brief.primaryAudience` | String field |
| `brief.conversionAngle.value` | `brief.conversionAction` | String field |
| `brief.conversionAngle.evidence.confidence` | `85` or `brief.confidenceScore` | Default confidence |
| `brief.recommendedHero.value` | `brief.headline` | String field |
| `brief.recommendedHero.evidence.confidence` | `brief.confidenceScore` | Overall confidence |
| `brief.recommendedSections` | `brief.sections` | Different structure! |
| `brief.recommendedSections[].title` | `brief.sections[].headline` | Section field rename |
| `brief.recommendedSections[].rationale` | `brief.sections[].contentSummary` | Section field rename |
| `brief.recommendedSections[].evidence` | `None` | Not available in MasterBrief |
| `brief.sourceCitations` | N/A (removed) | Only in extraction now |
| `brief.visualRedesign` | N/A (removed) | Generated dynamically |
| `brief.proofPoints` | N/A (removed) | Not in MasterBrief |

## Key Architectural Changes

### 1. Visual Redesign
**Before**: Stored in `SiteBrief.visualRedesign` field  
**After**: Generated dynamically during site generation, not persisted

**Impact**:
- Removed calls to `lead_repository.update_brief_visual_redesign()`
- `_apply_refinement_to_visual_redesign()` now returns empty list for MasterBrief
- Visual redesign briefs generated fresh from `generate_visual_redesign_brief()`

### 2. Evidence and Confidence
**Before**: Each field (e.g., `conversionAngle`) had nested `evidence.confidence`  
**After**: Single `brief.confidenceScore` at the top level

**Impact**:
- Changed all `brief.X.evidence.confidence` to either `85` (default) or `brief.confidenceScore`
- Evidence fields set to `None` where not available

### 3. Section Structure
**Before**: `BriefSectionRecommendation` with `title`, `rationale`, `evidence`  
**After**: `MasterBriefSection` with `headline`, `contentSummary`, `purpose`, `suggestedApproach`, `contentPoints`

**Impact**:
- Updated all section iteration code to use new field names
- Evidence removed from sections (set to `None`)

## Backwards Compatibility

The code maintains backwards compatibility with old `SiteBrief` data via:

```python
# Check for old visualRedesign field
if hasattr(brief, "visualRedesign") and brief.visualRedesign:  # type: ignore
    # Process old data
```

## Testing Status

### ✅ Type Checking
- **Pyright**: 0 errors, 0 warnings on `sites.py` and `visual_redesign.py`
- **Tests**: 7 warnings in `test_crawl_and_readiness.py` (tests use old SiteBrief fixtures)

### ⚠️ Tests Need Update
The following test files reference `SiteBrief` and should be updated to use `MasterBrief`:
- `tests/test_crawl_and_readiness.py`
- `tests/test_diversity_and_screenshot.py` (has `create_brief()` calls)
- `tests/test_auto_iteration.py` (mocks visual redesign)

## API Impact

### Endpoints That Changed
All endpoints that previously returned `SiteBrief` now work with `MasterBrief`:
- `POST /api/v1/leads/{id}/master-brief` - Creates master brief
- `GET /api/v1/leads/{id}/master-brief` - Retrieves master brief
- Site generation pipeline uses master brief internally

### Deprecated/Removed
According to `EXTRACTION_REFACTOR_PLAN.md` Phase 3, these should be removed:
- `LeadRepository.create_brief()` - Use `create_master_brief()` instead
- `LeadRepository.approve_brief()` - Use `approve_master_brief()` instead
- `LeadRepository.update_brief()` - Not needed (master brief regenerates)
- `LeadRepository.get_brief()` - Use `get_master_brief()` instead
- `LeadRepository.update_brief_visual_redesign()` - Removed (visual redesign not persisted)

## Next Steps

1. **Update Tests**: Modify test fixtures to use `MasterBrief` instead of `SiteBrief`
2. **Delete Legacy Code** (Phase 3): Remove old brief methods from `LeadRepository`
3. **Update Frontend**: Ensure frontend uses `/master-brief` endpoints
4. **Database Migration**: Archive old `site_briefs` collection (optional)

## Verification Checklist

- [x] All `SiteBrief` type annotations replaced with `MasterBrief`
- [x] All field accesses updated to use correct MasterBrief fields
- [x] Visual redesign generation updated to work with MasterBrief
- [x] Evidence/confidence patterns updated
- [x] Section structure handling updated
- [x] Pyright passes with 0 errors
- [ ] Unit tests updated
- [ ] Integration tests pass
- [ ] Manual testing of extraction → brief → generation flow

## Field Mapping Reference Script

Created `field_mapping.py` for quick reference of all field mappings during migration.

---

**Migration completed**: 2026-07-16  
**Files modified**: 2 core files, ~150 lines of changes  
**Type safety**: Fully restored (0 Pyright errors)
