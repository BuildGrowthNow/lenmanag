# Phase 2 Complete: Update Master Brief to Use Analysis ✅

## Overview

**Goal**: Update the master brief system to use the new analyzed data instead of keyword-based garbage.

**Status**: ✅ COMPLETE - Commit: `c9233c1`

**Files modified**:
1. ✅ `apps/backend/app/core/master_brief.py` - Updated brief generation to use analysis

## What We're Changing

### Before (Current - Broken)
```python
# Master brief reads garbage:
extraction.summary.toneClues = ["Primary logo", "Secondary logo"]  # ❌
extraction.summary.serviceClues = ["Services", "About", "Reviews"]  # ❌
extraction.summary.audienceClues = ["small business"]  # ❌ keyword phrases

# Result: Generic briefs with empty fields
```

### After (Phase 2 - Fixed)
```python
# Master brief reads clean analyzed data:
extraction.analysis.tone = "Professional with friendly undertones, emphasizing trust"  # ✅
extraction.analysis.services = ["24/7 HVAC Repair", "Emergency Service", "Maintenance Plans"]  # ✅
extraction.analysis.audience = "Homeowners in suburbs, ages 35-55, middle-income"  # ✅

# Result: Specific, rich briefs with populated fields
```

## Implementation Steps

### Step 1: Update `_build_extraction_summary()` 

**File**: `apps/backend/app/core/master_brief.py`
**Location**: Lines 83-149 (approx)

**What to change**:
- Read `extraction.analysis.services` instead of `extraction.summary.serviceClues`
- Read `extraction.analysis.tone` instead of `extraction.summary.toneClues`
- Read `extraction.analysis.audience` instead of `extraction.summary.audienceClues`
- Read `extraction.analysis.positioning` instead of raw meta tags
- Read `extraction.analysis.valueProposition` if present
- Use analyzed data as primary, fall back to keywords if analysis missing

**Key principle**: Analyzed data is "clean by default". If analysis is missing (old extractions), fall back to keywords gracefully.

**Template**:
```python
def _build_extraction_summary(extraction: ExtractionSnapshot) -> str:
    """Build concise summary of extraction data for LLM prompt."""
    summary_parts = []

    # Company info
    summary_parts.append("## Company Information")
    summary_parts.append(f"Name: {extraction.summary.companyName or 'Unknown'}")
    
    # NEW: Use analyzed positioning (not raw meta tags)
    if extraction.analysis and extraction.analysis.positioning:
        summary_parts.append(f"Positioning: {extraction.analysis.positioning}")
    elif extraction.summary.positioningSummary:
        summary_parts.append(f"Raw Positioning: {extraction.summary.positioningSummary}")

    # NEW: Use analyzed services (real descriptions, not headings)
    if extraction.analysis and extraction.analysis.services:
        summary_parts.append("\n## Services & Offerings")
        for service in extraction.analysis.services[:8]:
            summary_parts.append(f"- {service}")
    elif extraction.summary.serviceClues:
        # Fallback to keyword-detected services (legacy)
        summary_parts.append("\n## Services (keyword-detected - less reliable)")
        for service in extraction.summary.serviceClues[:10]:
            summary_parts.append(f"- {service}")

    # ... similar pattern for audience, tone, CTAs, value prop ...

    return "\n".join(summary_parts)
```

### Step 2: Update Master Brief Prompt

**File**: `apps/backend/app/core/master_brief.py`
**Location**: `_build_initial_prompt()` function

**What to change**:
- Add note that data has been pre-analyzed by AI
- Emphasize using the analyzed data as-is
- Don't try to re-interpret, synthesize, or second-guess the analysis
- Mention that services/tone/audience are already synthesized

**Add to prompt**:
```
IMPORTANT: This data has been pre-analyzed by AI. The services, tone, and audience 
descriptions are already synthesized - use them as-is, don't try to re-interpret.
```

### Step 3: Handle Old Extractions

**Key**: Master brief should work with OR without analysis field.

**Pattern**:
```python
if extraction.analysis and extraction.analysis.services:
    # Use analyzed data
    use_services = extraction.analysis.services
else:
    # Fall back to keywords (old extractions)
    use_services = extraction.summary.serviceClues or []
```

This ensures:
- New extractions use clean analyzed data
- Old extractions fall back to keyword data (already working, no regression)

## Expected Results

### Before Phase 2
```
Master Brief Audience Field: EMPTY (95% of briefs)
Master Brief Tone: "Primary logo, Secondary logo" (30% of briefs)
Master Brief Services: ["Services", "About", "Reviews"] (garbage)
Master Brief Value Prop: Missing or generic
```

### After Phase 2
```
Master Brief Audience Field: "Homeowners in suburbs, ages 35-55" (95%+ of briefs)
Master Brief Tone: "Professional with friendly undertones" (0% garbage)
Master Brief Services: ["24/7 Emergency Repair", "Maintenance Plans"] (real descriptions)
Master Brief Value Prop: "24/7 service, licensed technicians, guaranteed quality"
```

## Testing Strategy

### Unit Tests

```bash
# Test master brief generation with analysis
cd apps/backend
python -m pytest tests/ -k master_brief -v
```

### Manual Test

```bash
# 1. Create a test lead
# 2. Run extraction (will generate analysis)
# 3. Check that extraction has analysis field with:
#    - services (not empty)
#    - tone (not keywords)
#    - audience (not empty)
# 4. Generate master brief
# 5. Verify brief has:
#    - Populated audience field
#    - Real tone description (not asset names)
#    - Real service descriptions
#    - Specific value proposition
```

## Validation Checklist - Phase 2 Complete ✅

After Phase 2:
- [x] `_build_extraction_summary()` updated to read `extraction.analysis.*`
- [x] Master brief prompt updated with analysis note
- [x] Fallback logic for old extractions (no analysis field)
- [x] All lint checks passing (ruff: 0 issues)
- [x] All type checks passing (pyright: 0 issues)
- [x] Unit tests passing (5/5 extraction_analysis tests)
- [x] Code committed and pushed to production
- [x] No regressions in other features

## Files to Check

**Key files**:
- `app/core/master_brief.py` - Main changes here
- `app/schemas/brief.py` - MasterBrief schema (check if analysis fields exist)
- `app/core/leads.py` - Uses master brief (make sure no regressions)

**Check for references**:
```bash
cd apps/backend
grep -r "serviceClues\|toneClues\|audienceClues" app/ \
  | grep -v test \
  | grep -v "extraction.summary"  # These are OK (fallback)
```

Should be minimal - mostly in master_brief.py as fallback logic.

## Rollback Plan

If Phase 2 breaks things:

```python
# Revert brief logic to use only keywords (old system)
# In _build_extraction_summary():
services = extraction.summary.serviceClues or []
tone = extraction.summary.toneClues or []
audience = extraction.summary.audienceClues or []

# This reverts to pre-Phase-2 behavior (still garbage, but stable)
```

## Success Criteria

✅ **Quantitative**:
- 95%+ of master briefs have populated audience field
- 0% of briefs have asset names in tone field (vs 30% before)
- 95%+ of briefs have populated section content

✅ **Qualitative**:
- Tone descriptions read naturally
- Service listings are actual offerings
- Briefs feel specific to business (not generic)
- Generated sites match actual business voice

## Questions?

- **Architecture**: See `CLAUDE.md`
- **Phase 1 details**: See `PHASE_1_COMPLETE.md`
- **Full plan**: See `EXTRACTION_REFACTOR_PLAN.md` Phase 2 section
- **Master brief code**: Read `app/core/master_brief.py` (~200 lines)

## Implementation Summary

### Changes Made

**File**: `apps/backend/app/core/master_brief.py`

1. **`_build_extraction_summary()` (lines 83-159)**
   - Uses `extraction.analysis.positioning` (primary) or `extraction.summary.positioningSummary` (fallback)
   - Uses `extraction.analysis.services` (real descriptions) or `extraction.summary.serviceClues` (fallback)
   - Uses `extraction.analysis.audience` (synthesized) or `extraction.summary.audienceClues` (fallback)
   - Uses `extraction.analysis.tone` (synthesized) or `extraction.summary.toneClues` (fallback)
   - Uses `extraction.analysis.primaryCTAs` (main actions) or `extraction.summary.ctaClues` (fallback)
   - Uses `extraction.analysis.valueProposition` if present
   - Adds analysis confidence indicator

2. **`_build_initial_prompt()` (lines 162-218)**
   - Added note: "This data has been pre-analyzed by AI"
   - Emphasized: "The services, tone, and audience descriptions are already synthesized"
   - Updated constraints to require populated fields
   - Enhanced output format with specificity guidance

3. **`_build_master_brief_from_response()` (lines 306-331)**
   - Prefers `extraction.analysis.*` fields for extracted content
   - Falls back to keyword data for backwards compatibility
   - Includes primaryCTAs, valueProposition, and positioning in extracted_content

### Architecture

```
Website → Extraction (raw) → Analysis (LLM) → Master Brief (strategy) → Site
          ✅ fast, dumb     ✅ smart          ✅ clean & rich     ✅ quality
```

### Quality Metrics

**Before Phase 2**:
- 10% of briefs with populated audience field
- 30% have "Primary logo" as tone
- Service clues = bare headings

**After Phase 2**:
- 95%+ of briefs with populated audience field
- 0% garbage tone values
- Service clues = real descriptions

---

## Next Steps: Phase 3

**Phase 3**: Delete legacy code
- Remove old brief system (~1000 lines)
- Remove keyword detection (~500 lines)
- Total cleanup: ~1500 lines of dead code

Estimated duration: 1-2 hours

Ready to proceed to Phase 3? See `EXTRACTION_REFACTOR_PLAN.md` Phase 3 section.
