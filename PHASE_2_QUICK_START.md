# Phase 2 Quick Start: Update Master Brief to Use Analysis

## Overview

**Goal**: Update the master brief system to use the new analyzed data instead of keyword-based garbage.

**Duration**: 1-2 hours

**Files to modify**:
1. `apps/backend/app/core/master_brief.py` - Update brief generation to use analysis

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

## Validation Checklist

After Phase 2:
- [ ] `_build_extraction_summary()` updated to read `extraction.analysis.*`
- [ ] Master brief prompt updated with analysis note
- [ ] Fallback logic for old extractions (no analysis field)
- [ ] All lint checks passing
- [ ] All type checks passing
- [ ] Unit tests passing
- [ ] Manual test with 3+ different sites
- [ ] Compare old vs new brief quality - verify improvement
- [ ] No regressions in other features

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

## Next Steps After Phase 2

**Phase 3**: Delete legacy code
- Remove old brief system (~1000 lines)
- Remove keyword detection (~500 lines)
- Total cleanup: ~1500 lines of dead code

---

**Ready to implement Phase 2?** ✅

Start by reading `app/core/master_brief.py` to understand current structure, then update `_build_extraction_summary()` to use analyzed data with fallback to keywords.
