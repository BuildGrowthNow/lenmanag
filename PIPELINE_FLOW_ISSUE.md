# Pipeline Flow Issue - Quick Reference

## Current Problem (BROKEN)

```
┌─────────────────────────────────────────────────────────────────┐
│ Auto Pipeline - Line 666 in leads.py                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   await self.create_brief(lead_id)  ❌ WRONG                   │
│                                                                  │
│   This calls the OLD deterministic brief builder!               │
│   - Uses keyword-detected "toneClues" (garbage)                 │
│   - Uses keyword-detected "serviceClues" (headings only)        │
│   - Produces shallow briefs with empty fields                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

Meanwhile, there's a **NEW** system that's better but not used:

```
┌─────────────────────────────────────────────────────────────────┐
│ Master Brief System - Line 2778 in leads.py                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   await self.create_master_brief(lead_id)  ✅ CORRECT          │
│                                                                  │
│   This calls the NEW AI-powered master brief!                   │
│   - Uses LLM to generate strategy                               │
│   - Produces rich briefs with populated fields                  │
│   - But NOT used in auto pipeline!                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## The Fix (Phase 0)

**File**: `apps/backend/app/core/leads.py`

**Line 666**: Change this:
```python
brief = await self.create_brief(lead_id)  # ❌
```

**To this**:
```python
master_brief = await self.create_master_brief(lead_id)  # ✅
```

**Then add approval** (line ~676):
```python
# OLD (line 675):
await self.approve_brief(lead_id, approved_by="auto")  # ❌

# NEW:
await self.approve_master_brief(
    lead_id=lead_id,
    approved_by="auto",
    notes="Auto-approved in pipeline"
)  # ✅
```

## Sequential Flow (Correct)

```python
# Each step WAITS for the previous to complete

# Step 1: Extraction
crawl_data = await crawl_website(url)
await save_extraction(crawl_data)
# ↓ extraction.crawlStatus = "completed"

# Step 2: Analysis (NEW - Phase 1)
analysis = await analyze_extraction(extraction)
await update_extraction_with_analysis(extraction, analysis)
# ↓ extraction.analysis = { services, tone, CTAs, ... }

# Step 3: Master Brief
master_brief = await create_master_brief(lead_id)
# ↓ master_brief uses extraction.analysis (clean data)

# Step 4: Approve
await approve_master_brief(lead_id, approved_by="auto")
# ↓ master_brief.approvalState = "approved"

# Step 5: Site Generation
await queue_generation_job(lead_id)
# ↓ generation job reads master_brief
```

**Key**: All `await` statements are blocking. Next step CANNOT start until previous completes.

## Why This Matters

**Current (BROKEN)**:
```
Extraction → OLD Brief (garbage data) → Site Generation
                ↓
          "tone: Primary logo"  ❌
          "services: Services, About"  ❌
          Empty audience field  ❌
```

**After Phase 0 Fix**:
```
Extraction → Master Brief (AI strategy) → Site Generation
                ↓
          "tone: Professional with friendly..."  ✅
          "services: 24/7 HVAC Repair, Installation"  ✅
          Populated audience: "Homeowners 35-55..."  ✅
```

**After Phase 1 (Analysis Layer)**:
```
Extraction → Analysis (LLM semantics) → Master Brief → Site Generation
                ↓                            ↓
          Clean analyzed data          Uses analysis (not keywords)
```

## Testing Phase 0

```bash
# Create a lead in auto mode
curl -X POST http://localhost:8000/api/v1/leads \
  -H "Cookie: lenquant_session=$SESSION" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Auto Pipeline",
    "email": "test@example.com",
    "companyName": "Test Company",
    "websiteUrl": "https://championwelldrilling.com",
    "pipelineMode": "auto"
  }'

# Watch logs
tail -f apps/backend/logs/lenquant.log

# Should see (in order):
# 1. "Extraction complete"
# 2. "Master brief generated"  ← Not "Brief generated"
# 3. "Master brief approved"
# 4. "Site generation started"

# Check the brief in DB:
# db.master_briefs.findOne({leadId: "..."})
# Should have:
# - toneAndVoice: "Professional with..." (NOT "Primary logo")
# - sections: [7 items with real content]
# - approvalState: "approved"
```

## Quick Checklist

Before starting Phase 1:

- [ ] Phase 0 implemented (auto pipeline uses master brief)
- [ ] `approve_master_brief()` method exists
- [ ] Sequential flow verified (each step waits)
- [ ] Tested with auto mode lead end-to-end
- [ ] Master brief has approval fields in schema
- [ ] Site generation reads master brief (not old brief)

Once Phase 0 is done → Ready for Phase 1 (Analysis Layer).
