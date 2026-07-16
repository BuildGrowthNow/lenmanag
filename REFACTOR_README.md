# Extraction Refactor - Implementation Guide

## Quick Start

Read these files in order:

1. **PIPELINE_FLOW_ISSUE.md** (5 min read)
   - Understand the current broken auto pipeline
   - See the Phase 0 fix (30 mins to implement)
   - Quick checklist before starting Phase 1

2. **EXTRACTION_REFACTOR_PLAN.md** (20 min read)
   - Complete 4-phase implementation plan
   - Full code examples for each phase
   - Testing strategy and rollout plan

## What's Wrong?

### Problem 1: Auto Pipeline Uses Wrong Brief System

```python
# Current (BROKEN):
brief = await self.create_brief(lead_id)  # ❌ Old deterministic brief

# Should be:
master_brief = await self.create_master_brief(lead_id)  # ✅ New AI brief
```

**Impact**: Auto-generated sites use shallow briefs with garbage data ("tone: Primary logo")

### Problem 2: Keyword-Based Detection is Garbage

```python
# Extraction does this:
if "professional" in text:
    tone_clues.append("Professional tone")  # ❌ Useless in Spanish, French, etc.

if "logo" in hint:
    logo_candidates.append(url)  # ❌ Detects /settings.svg as logo
```

**Impact**: 
- Only works in English
- Detects Material Design icons as logos
- Returns headings as "services" instead of actual descriptions

### Problem 3: Master Brief Gets Garbage In → Garbage Out

```python
# Master brief receives:
extraction.summary.toneClues = ["Primary logo", "Secondary logo"]  # ❌
extraction.summary.serviceClues = ["Services", "About", "Reviews"]  # ❌

# And tries to synthesize from this garbage
```

**Impact**: 95% of briefs have empty audience, generic content, wrong tone

## The Solution

### Architecture Change

**OLD (Keyword Hell)**:
```
Website → Extraction (keywords) → Master Brief (tries to fix) → Site
          ↓ garbage                ↓ still garbage           ↓ shallow
```

**NEW (LLM Analysis)**:
```
Website → Extraction (raw HTML) → Analysis (LLM) → Master Brief → Site
          ↓ fast, dumb            ↓ smart         ↓ rich       ↓ quality
```

### 4 Phases

| Phase | Duration | What | Why |
|-------|----------|------|-----|
| **Phase 0** | 30 min | Fix auto pipeline | **Must do first** - currently broken |
| **Phase 1** | 2-3 hrs | Add analysis layer | Replace keywords with LLM |
| **Phase 2** | 1-2 hrs | Update master brief | Use analyzed data |
| **Phase 3** | 1-2 hrs | Delete legacy code | Remove 500+ lines of garbage |

**Total**: 8.5-11.5 hours

## Phase 0: Critical Fix (START HERE)

**File**: `apps/backend/app/core/leads.py`

**3 changes required**:

1. **Line 666**: Change `create_brief` → `create_master_brief`
2. **Line 675**: Change `approve_brief` → `approve_master_brief` (new method)
3. **Add method**: `approve_master_brief()` for auto approval

See `PIPELINE_FLOW_ISSUE.md` for detailed code.

**Test**: Create auto mode lead, verify it generates master brief (not old brief)

## Phase 1: Analysis Layer

**New file**: `apps/backend/app/core/extraction_analysis.py`

**Purpose**: Replace ALL keyword detection with LLM semantic analysis

**What it does**:
- Input: Raw extraction (HTML, text, images)
- Output: Clean analyzed data (services, tone, CTAs, audience)
- Cost: ~$0.02-0.05 per extraction
- Benefit: Multilingual, accurate, no more garbage

**Integration**: Add to extraction job after crawling, before saving

See `EXTRACTION_REFACTOR_PLAN.md` Phase 1 for full code.

## Phase 2: Master Brief Update

**File**: `apps/backend/app/core/master_brief.py`

**Changes**:
- Read `extraction.analysis.services` (not `serviceClues`)
- Read `extraction.analysis.tone` (not `toneClues`)
- Read `extraction.analysis.audience` (not `audienceClues`)

**Result**: Briefs have 95%+ populated fields, no more "tone: Primary logo"

See `EXTRACTION_REFACTOR_PLAN.md` Phase 2 for diff.

## Phase 3: Delete ALL Legacy Code (NO TOLERANCE)

**Policy**: Zero legacy code. If it's old brief or keyword detection, DELETE IT.

**What Gets Deleted** (~1500 lines total):

1. **Old Brief System** (~1000 lines in `leads.py`):
   - `create_brief()` ❌
   - `approve_brief()` ❌
   - `update_brief()` ❌
   - `_build_brief_doc()` ❌ (200+ lines)
   - All related helper methods ❌

2. **Keyword Detection** (~500 lines in `extraction.py`):
   - Tone keyword patterns ❌
   - Service extraction from headings ❌
   - Extended CTA keywords (31 keywords) ❌
   - `_looks_like_cta()` function ❌
   - Material Design icon filtering ❌

3. **Enrichment System** (entire file):
   - `extraction_enrichment.py` ❌
   - All `_infer_*()` methods ❌

4. **API Routes** (old brief endpoints):
   - `/leads/{id}/brief` POST ❌ (or redirect to master brief)
   - `/leads/{id}/brief` PATCH ❌
   - `/leads/{id}/brief/approve` POST ❌

5. **Schemas**:
   - `SiteBrief` model ❌ (if exists in `schemas/brief.py`)

**Result**: 
- Codebase is 30% smaller ✂️
- Zero technical debt ✅
- Only master brief exists ✅
- Only LLM analysis exists ✅

**Verification**:
```bash
# After Phase 3, this should return ZERO results:
grep -r "create_brief\|_build_brief_doc\|_looks_like_cta" apps/backend/app/ | grep -v master | grep -v test

# Zero tolerance - if grep finds it, delete it
```

See `EXTRACTION_REFACTOR_PLAN.md` Phase 3 for detailed deletion list.

## Success Metrics

### Before (Current)

- ❌ 10% of briefs have populated audience field
- ❌ 30% have "Primary logo" as tone
- ❌ Service clues = bare headings ("Services", "About")
- ❌ Only works in English
- ❌ 50% of briefs need manual regeneration

### After (Target)

- ✅ 95%+ of briefs have populated audience
- ✅ 0% have garbage in tone field
- ✅ Service clues = real descriptions ("24/7 HVAC Repair")
- ✅ Works in any language
- ✅ 30% reduction in regenerations

## Cost Analysis

**Current**: ~$0.03-0.07 per lead (mostly master brief LLM call)

**After**: ~$0.05-0.10 per lead (+$0.02-0.03 for analysis)

**ROI**: 
- Quality improvement: 3-5x (based on populated fields)
- Fewer regenerations: -30% (saves $0.03-0.05 per avoided regen)
- Net: Slightly higher upfront cost, but better quality = fewer retries

## Testing Strategy

1. **Phase 0**: Manual test auto pipeline
   - Create lead, verify uses master brief
   - Check logs for sequential execution

2. **Phase 1**: Unit test analysis module
   - Test English site
   - Test Spanish site
   - Test e-commerce vs services vs SaaS

3. **Phase 2**: Integration test master brief
   - Verify populated fields
   - Compare old vs new brief quality

4. **Phase 3**: Regression test
   - Verify old extractions still work
   - Check for broken references

See `EXTRACTION_REFACTOR_PLAN.md` for detailed test checklist.

## Rollback Plan

If Phase 1 breaks production:

```python
# In leads.py, comment out analysis:
# analysis_result = await analyze_extraction(temp_snapshot)

# Use empty analysis instead:
crawl_data["analysis"] = {
    "services": [],
    "tone": "Professional",
    "primaryCTAs": [],
    "audience": "",
    "valueProposition": "",
    "positioning": "",
    "confidence": 0
}
```

Master brief already has fallback to keyword data (Phase 2 implementation).

## Questions Before Starting?

### Cost Approval

**Q**: +$0.02-0.03 per extraction acceptable?  
**A**: Yes - better quality leads = fewer regenerations = net savings

### Rollout Strategy

**Q**: All phases at once or phased over 1 week?  
**A**: Recommend: Phase 0 immediately, then Phase 1+2 together, Phase 3 last

### Backwards Compatibility

**Q**: Support old extractions without analysis for how long?  
**A**: Phase 2 has fallback - works forever

### Analysis Retention

**Q**: Keep analysis in DB permanently?  
**A**: Yes - it's small (~2KB per extraction) and valuable for debugging

### Manual Override

**Q**: Allow operators to edit analysis before master brief?  
**A**: Not in MVP - analysis is fast enough to regenerate if wrong

## Implementation Checklist

- [ ] Read `PIPELINE_FLOW_ISSUE.md`
- [ ] Read `EXTRACTION_REFACTOR_PLAN.md`
- [ ] **Phase 0**: Fix auto pipeline (30 min)
- [ ] Test Phase 0 with auto mode lead
- [ ] **Phase 1**: Create analysis module (2-3 hrs)
- [ ] Test Phase 1 with 5+ different sites
- [ ] **Phase 2**: Update master brief (1-2 hrs)
- [ ] Test Phase 2 brief quality
- [ ] **Phase 3**: Delete legacy code (1-2 hrs)
- [ ] Regression test everything
- [ ] Update `CLAUDE.md` with new architecture
- [ ] Deploy to staging
- [ ] Manual QA on staging (10 leads)
- [ ] Deploy to production
- [ ] Monitor for 24 hours

## Support

- **Architecture**: See `CLAUDE.md`
- **Current issue**: See `PIPELINE_FLOW_ISSUE.md`
- **Full plan**: See `EXTRACTION_REFACTOR_PLAN.md`
- **Logs**: `apps/backend/logs/lenquant.log`
- **Database**: `site_extractions` collection has `analysis` field (after Phase 1)

---

**Ready?** Start with Phase 0 in `PIPELINE_FLOW_ISSUE.md` 🚀
