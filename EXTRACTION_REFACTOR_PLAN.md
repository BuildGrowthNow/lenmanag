# Extraction Refactor: LLM Analysis Layer Implementation Plan

## ⚠️ CRITICAL FIXES REQUIRED FIRST

Before implementing the analysis layer, you **MUST** fix the auto pipeline:

1. **Wrong brief system**: Auto pipeline calls `create_brief()` (old deterministic) instead of `create_master_brief()` (new AI)
2. **Sequential execution**: All steps must complete before next starts (extraction → analysis → brief → generation)
3. **Master brief approval**: Need `approve_master_brief()` method for auto pipeline

**Start with Phase 0 before Phase 1!**

---

## Executive Summary

**Problem**: Current extraction uses keyword-based heuristics that produce garbage data (asset labels as "tone", bare headings as "services", English-only detection). This garbage flows into master briefs, resulting in shallow, generic landing pages.

**Solution**: Insert an LLM analysis layer between extraction and master brief generation. Remove all keyword-based semantic analysis.

**Impact**: 
- ✅ Multilingual support (no more English-only keywords)
- ✅ Accurate tone/voice detection (actual synthesis vs keyword matching)
- ✅ Real service descriptions (not just headings)
- ✅ Clean master briefs with populated fields
- ✅ Reduced code complexity (delete 500+ lines of keyword heuristics)

---

## Current Architecture (BROKEN)

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. EXTRACTION (extraction.py)                                   │
│    - Crawls HTML                                                │
│    - Keyword detection for services, tone, CTAs ❌ GARBAGE     │
│    - Language-dependent ❌                                      │
│    - Produces: toneClues=["Primary logo", "Secondary logo"]     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. ENRICHMENT (extraction_enrichment.py)                        │
│    - Only runs if content is "sparse" ❌ WRONG LOGIC           │
│    - LLM tries to fix keyword garbage                           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. MASTER BRIEF (master_brief.py)                               │
│    - Receives garbage: "Tone: Primary logo, Secondary logo"     │
│    - Tries to synthesize strategy from bad inputs               │
│    - Results: Empty fields, generic content ❌                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Target Architecture (CLEAN)

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. EXTRACTION (extraction.py) - DUMB & FAST                     │
│    - Crawls HTML/text/images                                    │
│    - NO semantic analysis                                       │
│    - NO keyword matching                                        │
│    - Output: Raw signals only                                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. ANALYSIS (extraction_analysis.py) - NEW MODULE ✨            │
│    - LLM analyzes ALL extractions (not just sparse ones)        │
│    - Detects: services, tone, CTAs, audience, positioning       │
│    - Language-agnostic ✅                                       │
│    - Output: Clean semantic data                                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. MASTER BRIEF (master_brief.py) - SYNTHESIS                   │
│    - Receives clean analyzed data                               │
│    - LLM synthesizes landing page strategy                      │
│    - Results: Rich briefs with populated fields ✅              │
└─────────────────────────────────────────────────────────────────┘
```

---

## CRITICAL: Pipeline Flow Fix

### Current Problem

The auto pipeline has **TWO BRIEF SYSTEMS** running simultaneously:

```python
# apps/backend/app/core/leads.py Line 666
brief = await self.create_brief(lead_id)  # ❌ OLD deterministic brief
```

But there's also:

```python
# Line 2778
master_brief = await self.create_master_brief(lead_id)  # ✅ NEW AI brief
```

**The auto pipeline is calling the WRONG ONE!**

### Required Sequential Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. EXTRACTION                                                    │
│    crawl_website() → save to DB                                 │
│    Status: "extracted"                                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓ WAIT (extraction must be saved)
┌─────────────────────────────────────────────────────────────────┐
│ 2. ANALYSIS (NEW - Phase 1)                                     │
│    analyze_extraction() → update extraction.analysis in DB      │
│    LLM extracts: services, tone, CTAs, audience                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓ WAIT (analysis must complete)
┌─────────────────────────────────────────────────────────────────┐
│ 3. MASTER BRIEF                                                  │
│    create_master_brief() → save to DB                           │
│    Uses: extraction.analysis (clean data)                       │
│    Status: "briefing" → "brief_ready"                           │
└─────────────────────────────────────────────────────────────────┘
                              ↓ WAIT (brief must be approved)
┌─────────────────────────────────────────────────────────────────┐
│ 4. SITE GENERATION                                               │
│    queue_generation_job() → Celery worker                       │
│    Uses: master_brief (strategy + content)                      │
│    Status: "generating" → "qa" → "ready"                        │
└─────────────────────────────────────────────────────────────────┘
```

**Each step MUST complete before the next starts.**

### Auto vs Manual Mode

**Auto Mode**:
```python
# After extraction completes:
analysis = await analyze_extraction()  # WAIT
master_brief = await create_master_brief()  # WAIT
await approve_master_brief(approved_by="auto")  # WAIT
await queue_generation_job()  # WAIT
# → Lead goes from "extracting" to "ready" with no operator intervention
```

**Manual Mode**:
```python
# After extraction completes:
analysis = await analyze_extraction()  # WAIT
# PAUSE - operator reviews extraction
# Operator clicks "Generate Brief"
master_brief = await create_master_brief()  # WAIT
# PAUSE - operator reviews brief
# Operator clicks "Approve & Generate Site"
await approve_master_brief(approved_by=operator_id)  # WAIT
await queue_generation_job()  # WAIT
# PAUSE - operator reviews generated site in QA
```

### Pipeline Mode Behavior

- **Auto mode**: Run all steps sequentially without operator approval
- **Manual mode**: Pause after each step for operator approval

---

## Implementation Phases

### **PHASE 0: Fix Pipeline Flow** (30 mins) ⚠️ CRITICAL

**Goal**: Ensure auto pipeline uses master brief (not old brief) and runs sequentially.

#### 0.1 Update Auto Pipeline

**File**: `apps/backend/app/core/leads.py`

**FIND** (lines 662-686):
```python
if mode == "auto":
    # Auto mode: immediately generate brief
    await self._set_pipeline_stage(lead_id, "briefing")
    try:
        brief = await self.create_brief(lead_id)  # ❌ WRONG - old brief
        if brief is None:
            await self._set_pipeline_stage(
                lead_id,
                "needs_attention",
                detail="Brief generation returned no result.",
            )
            return
        # Auto-approve the brief
        await self.approve_brief(lead_id, approved_by="auto")
        await self.advance_pipeline_after_brief(lead_id)
```

**REPLACE WITH**:
```python
if mode == "auto":
    # Auto mode: immediately generate master brief
    await self._set_pipeline_stage(lead_id, "briefing")
    try:
        # Use NEW AI-powered master brief (not old deterministic brief)
        master_brief = await self.create_master_brief(lead_id)
        if master_brief is None:
            await self._set_pipeline_stage(
                lead_id,
                "needs_attention",
                detail="Master brief generation returned no result.",
            )
            return
        
        # Auto-approve the master brief
        await self.approve_master_brief(
            lead_id=lead_id,
            approved_by="auto",
            notes="Auto-approved in pipeline"
        )
        
        # WAIT for brief to be saved before advancing
        # (create_master_brief is already async and blocks until complete)
        
        # Now advance to site generation
        await self.advance_pipeline_after_brief(lead_id)
        
    except Exception:
        logging.getLogger("lenquant.pipeline").exception(
            "Auto master brief generation failed for lead %s", lead_id
        )
        await self._set_pipeline_stage(
            lead_id, "needs_attention", detail="Master brief generation failed."
        )
```

#### 0.2 Add Master Brief Approval Method

**File**: `apps/backend/app/core/leads.py`

Add new method after `create_master_brief`:

```python
async def approve_master_brief(
    self,
    *,
    lead_id: str,
    approved_by: str,
    notes: str | None = None,
) -> MasterBrief | None:
    """Approve a master brief and mark it ready for site generation."""
    await self._maybe_ensure_indexes()
    
    master_brief = await self.get_master_brief(lead_id)
    if master_brief is None:
        raise ValueError("no_master_brief_to_approve")
    
    # Update approval state
    database = get_database()
    if database is None:
        # Memory mode
        async with self._memory_lock:
            briefs = self._memory.setdefault("master_briefs", {}).get(lead_id, [])
            for brief_doc in briefs:
                if brief_doc["id"] == master_brief.id:
                    brief_doc["approvalState"] = "approved"
                    brief_doc["approvedBy"] = approved_by
                    brief_doc["approvedAt"] = _now().isoformat()
                    if notes:
                        brief_doc["approvalNotes"] = notes
                    return self._master_brief_doc_to_snapshot(brief_doc)
    else:
        # Database mode
        update_result = await database["master_briefs"].update_one(
            {"id": master_brief.id},
            {
                "$set": {
                    "approvalState": "approved",
                    "approvedBy": approved_by,
                    "approvedAt": _now().isoformat(),
                    **({"approvalNotes": notes} if notes else {}),
                }
            },
        )
        if update_result.modified_count == 0:
            return None
        
        updated_doc = await database["master_briefs"].find_one({"id": master_brief.id})
        if updated_doc:
            return self._master_brief_doc_to_snapshot(updated_doc)
    
    await self._record_brief_event(
        lead_id,
        event_type="master_brief_approved",
        event_name=f"Master brief approved by {approved_by}",
        version=master_brief.version,
    )
    
    return master_brief


def _master_brief_doc_to_snapshot(self, doc: dict[str, Any]) -> MasterBrief:
    """Convert database document to MasterBrief snapshot."""
    from app.schemas.brief import MasterBrief
    
    return MasterBrief(**doc)
```

#### 0.3 Verify Sequential Execution

The key is that all these methods are `async def` and use `await`, which means:

```python
# This is SEQUENTIAL (correct):
master_brief = await self.create_master_brief(lead_id)  # Step 1 - WAITS
await self.approve_master_brief(lead_id, approved_by="auto")  # Step 2 - WAITS
await self.advance_pipeline_after_brief(lead_id)  # Step 3 - WAITS
```

**NOT parallel**. Each `await` blocks until complete.

#### 0.4 Update Site Generation to Use Master Brief

**File**: `apps/backend/app/core/sites.py`

Find where site generation reads the brief and ensure it reads **master brief**:

```python
# FIND:
brief = await lead_repository.get_brief(lead_id)  # ❌ OLD

# REPLACE WITH:
master_brief = await lead_repository.get_master_brief(lead_id)  # ✅ NEW
if master_brief is None:
    raise ValueError("no_master_brief_for_generation")
```

#### 0.5 Test Phase 0

```bash
# Manual test auto pipeline:
# 1. Create lead in auto mode
# 2. Trigger extraction
# 3. Verify logs show:
#    - "Extraction complete"
#    - "Analyzing extraction with LLM" (after Phase 1)
#    - "Master brief generated"
#    - "Site generation started"
# 4. Check timing - each step should complete before next starts
```

---

### **PHASE 1: Create Analysis Module** (2-3 hours)

**Goal**: Build the new LLM analysis layer without breaking existing code.

#### 1.1 Create New Module

**File**: `apps/backend/app/core/extraction_analysis.py`

```python
"""
Extraction Analysis — LLM-Powered Semantic Understanding

Replaces keyword-based heuristics with actual semantic analysis.
Runs after raw extraction, before master brief generation.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.llm import get_llm_client
from app.schemas.extraction import ExtractionSnapshot

logger = logging.getLogger(__name__)


async def analyze_extraction(extraction: ExtractionSnapshot) -> dict[str, Any]:
    """
    Analyze raw extraction data using LLM to extract semantic meaning.
    
    This replaces ALL keyword-based detection with actual understanding:
    - Services: Real descriptions (not bare headings)
    - Tone: Synthesized voice description (not keyword matches)
    - CTAs: Primary conversion actions (not all buttons)
    - Audience: Synthesized target market (not keyword phrases)
    - Positioning: What they do and who for (not raw meta tags)
    
    Args:
        extraction: Raw extraction snapshot with HTML/text signals
        
    Returns:
        Dictionary with analyzed data:
        {
            "services": ["Service 1", "Service 2", ...],
            "tone": "Professional with friendly undertones...",
            "primaryCTAs": ["Schedule Consultation", "Get Quote"],
            "audience": "Homeowners in suburbs, ages 35-55, middle-income",
            "valueProposition": "What makes them different",
            "positioning": "Synthesized 2-3 sentence summary"
        }
    """
    llm = get_llm_client()
    
    # Gather content for analysis
    context = _build_analysis_context(extraction)
    
    # Single LLM call with structured output
    prompt = _build_analysis_prompt(context)
    
    try:
        response = await llm.generate_text(
            prompt=prompt,
            temperature=0.3,  # Lower temp for more consistent analysis
            max_tokens=2048,
        )
        
        # Parse structured JSON response
        analysis = llm.extract_json_from_response(response)
        
        # Validate and clean
        cleaned_analysis = _validate_analysis(analysis)
        
        logger.info(
            "Analysis complete: %d services, tone='%s', %d CTAs",
            len(cleaned_analysis.get("services", [])),
            cleaned_analysis.get("tone", "")[:50],
            len(cleaned_analysis.get("primaryCTAs", []))
        )
        
        return cleaned_analysis
        
    except Exception as e:
        logger.error("LLM analysis failed: %s", e)
        # Return empty analysis rather than failing
        return _empty_analysis()


def _build_analysis_context(extraction: ExtractionSnapshot) -> dict[str, Any]:
    """Extract relevant content from extraction for LLM analysis."""
    
    # Gather all text content (homepage + top pages)
    all_text_chunks = []
    
    for page in extraction.pageInventory[:3]:  # Homepage + 2 key pages
        if hasattr(page, "cleanedText") and page.cleanedText:
            all_text_chunks.append(page.cleanedText[:3000])
        elif hasattr(page, "summary") and page.summary:
            all_text_chunks.append(page.summary)
    
    # Section content
    section_texts = []
    section_headings = []
    for section in extraction.sectionInventory[:10]:
        if hasattr(section, "model_dump"):
            section_data = section.model_dump()
        else:
            section_data = dict(section) if hasattr(section, "__iter__") else {}
        
        if section_data.get("heading"):
            section_headings.append(section_data["heading"])
        if section_data.get("text"):
            section_texts.append(section_data["text"][:500])
    
    # All CTAs (buttons, links with action text)
    all_ctas = extraction.summary.ctaClues if extraction.summary.ctaClues else []
    
    return {
        "company_name": extraction.summary.companyName or "this company",
        "website_url": extraction.canonicalWebsiteUrl,
        "homepage_text": all_text_chunks[0] if all_text_chunks else "",
        "additional_pages_text": "\n\n".join(all_text_chunks[1:3]),
        "section_headings": section_headings,
        "section_texts": section_texts,
        "all_ctas": all_ctas[:20],  # Limit to first 20
        "raw_positioning": extraction.summary.positioningSummary or "",
    }


def _build_analysis_prompt(context: dict[str, Any]) -> str:
    """Build the LLM prompt for extraction analysis."""
    
    prompt = f"""You are analyzing a business website to extract semantic meaning for landing page generation.

# Company Information
Name: {context['company_name']}
Website: {context['website_url']}

# Homepage Content
{context['homepage_text'][:6000]}

# Additional Page Content
{context['additional_pages_text'][:3000]}

# Section Headings Found
{chr(10).join(f"- {h}" for h in context['section_headings'][:15])}

# All CTA Buttons/Links Found
{chr(10).join(f"- {cta}" for cta in context['all_ctas'][:20])}

---

## Task
Analyze this content and extract semantic meaning. Return a JSON object with:

1. **services** (array of strings): 3-8 actual services/products they offer
   - Use real descriptions, not generic headings
   - Example: "24/7 Emergency HVAC Repair" NOT "Services"
   
2. **tone** (string): Synthesized tone/voice description in 1-2 sentences
   - Examples: "Professional with friendly undertones, emphasizing trust and reliability"
   - NOT just keywords like "professional" or "friendly"
   
3. **primaryCTAs** (array of 1-3 strings): The PRIMARY conversion actions
   - Only the main CTAs (not "Contact Us" if there's a stronger CTA)
   - Example: ["Schedule Free Consultation", "Get Instant Quote"]
   
4. **audience** (string): Target audience in 1 sentence
   - Be specific: demographics, needs, context
   - Example: "Homeowners in suburbs experiencing HVAC issues, ages 35-55, middle-income"
   
5. **valueProposition** (string): What makes them different/valuable in 1-2 sentences
   - Not generic ("we provide great service")
   - Specific differentiators
   
6. **positioning** (string): Synthesized summary in 2-3 sentences
   - What they do, who they serve, how they're different
   - NOT just repeating meta tags
   
7. **confidence** (number 0-100): How confident you are in this analysis

## Rules
- Base answers ONLY on the content provided
- If something is unclear, be conservative (lower confidence)
- Use the language of the content (if Spanish site, answer in Spanish)
- Be specific, not generic

Return ONLY valid JSON, no markdown formatting:
{{
  "services": ["Service 1", "Service 2", ...],
  "tone": "Tone description...",
  "primaryCTAs": ["CTA 1", "CTA 2"],
  "audience": "Audience description...",
  "valueProposition": "Value prop...",
  "positioning": "Positioning summary...",
  "confidence": 85
}}
"""
    
    return prompt


def _validate_analysis(analysis: dict[str, Any]) -> dict[str, Any]:
    """Validate and clean LLM analysis response."""
    
    return {
        "services": [
            str(s).strip() 
            for s in analysis.get("services", [])
            if s and len(str(s).strip()) > 5
        ][:8],
        "tone": str(analysis.get("tone", "")).strip()[:500] or "Professional",
        "primaryCTAs": [
            str(c).strip()
            for c in analysis.get("primaryCTAs", [])
            if c and len(str(c).strip()) > 3
        ][:3],
        "audience": str(analysis.get("audience", "")).strip()[:300] or "General audience",
        "valueProposition": str(analysis.get("valueProposition", "")).strip()[:500] or "",
        "positioning": str(analysis.get("positioning", "")).strip()[:1000] or "",
        "confidence": min(100, max(0, int(analysis.get("confidence", 50)))),
    }


def _empty_analysis() -> dict[str, Any]:
    """Return empty analysis when LLM fails."""
    return {
        "services": [],
        "tone": "Professional",
        "primaryCTAs": [],
        "audience": "General audience",
        "valueProposition": "",
        "positioning": "",
        "confidence": 0,
    }
```

#### 1.2 Update Extraction Schema

**File**: `apps/backend/app/schemas/extraction.py`

Add new field to store analysis results:

```python
# Add to ExtractionSummary model (around line 40):

class ExtractionAnalysis(BaseModel):
    """LLM-analyzed semantic data from extraction."""
    services: list[str] = []
    tone: str = "Professional"
    primaryCTAs: list[str] = []
    audience: str = ""
    valueProposition: str = ""
    positioning: str = ""
    confidence: int = 0
    analyzedAt: datetime | None = None


class ExtractionSnapshot(BaseModel):
    # ... existing fields ...
    
    # NEW: Add analysis field
    analysis: ExtractionAnalysis | None = None
```

#### 1.3 Add Analysis to Extraction Job

**File**: `apps/backend/app/core/leads.py`

Update `run_extraction_job` to call analysis (around line 3011):

```python
async def run_extraction_job(self, *, lead_id: str, job_id: str, refresh: bool) -> None:
    # ... existing crawl code ...
    
    # Phase 1: Validate + LLM-enrich extraction if content is sparse
    is_valid, content_issues = validate_extraction_content(crawl_data)
    # ... existing enrichment code ...
    
    # NEW PHASE 2: ALWAYS analyze extraction with LLM
    await self._update_job(
        job_id,
        progress=70,
        step="Analyzing extraction with LLM",
        lead_ids=[lead_id],
    )
    
    try:
        from app.core.extraction_analysis import analyze_extraction
        from app.schemas.extraction import ExtractionAnalysis
        
        # Convert crawl_data to ExtractionSnapshot for analysis
        temp_snapshot = self._extraction_doc_to_snapshot({**crawl_data, "leadId": lead_id})
        
        # Run LLM analysis
        analysis_result = await analyze_extraction(temp_snapshot)
        
        # Store analysis in crawl_data
        crawl_data["analysis"] = {
            **analysis_result,
            "analyzedAt": _now().isoformat()
        }
        
        logger.info(
            "LLM analysis complete for %s: %d services, confidence=%d",
            lead_id,
            len(analysis_result.get("services", [])),
            analysis_result.get("confidence", 0)
        )
        
    except Exception as analysis_err:
        logger.warning("LLM analysis failed, continuing with extraction: %s", analysis_err)
        # Don't fail the job, just log and continue
        crawl_data["analysis"] = {
            "services": [],
            "tone": "Professional",
            "primaryCTAs": [],
            "audience": "",
            "valueProposition": "",
            "positioning": "",
            "confidence": 0,
            "analyzedAt": None
        }
    
    # ... rest of existing code (save to DB, etc) ...
```

#### 1.4 Test Phase 1

```bash
# Run extraction on a test lead
cd apps/backend
python -m pytest tests/ -k extraction -v

# Manual test:
# 1. Create a lead
# 2. Run extraction
# 3. Check DB: extraction doc should have "analysis" field with services, tone, etc
# 4. Verify master brief still works (uses old data for now)
```

---

### **PHASE 2: Update Master Brief to Use Analysis** (1-2 hours)

**Goal**: Switch master brief to use analyzed data instead of keyword garbage.

#### 2.1 Update Master Brief Input

**File**: `apps/backend/app/core/master_brief.py`

Replace `_build_extraction_summary` function (lines 83-149):

```python
def _build_extraction_summary(extraction: ExtractionSnapshot) -> str:
    """Build a concise summary of extraction data for the LLM prompt."""
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

    # NEW: Use analyzed audience (synthesized, not keyword phrases)
    if extraction.analysis and extraction.analysis.audience:
        summary_parts.append("\n## Target Audience")
        summary_parts.append(extraction.analysis.audience)
    elif extraction.summary.audienceClues:
        # Fallback
        summary_parts.append("\n## Audience Clues (keyword-detected)")
        for audience in extraction.summary.audienceClues[:5]:
            summary_parts.append(f"- {audience}")

    # NEW: Use analyzed tone (synthesized description, not keywords/asset labels)
    if extraction.analysis and extraction.analysis.tone:
        summary_parts.append("\n## Tone & Voice")
        summary_parts.append(extraction.analysis.tone)
    elif extraction.summary.toneClues:
        # Fallback (but this is often garbage like "Primary logo")
        summary_parts.append("\n## Tone Hints (keyword-detected - unreliable)")
        for tone in extraction.summary.toneClues[:3]:
            summary_parts.append(f"- {tone}")
    
    # NEW: Use analyzed primary CTAs (main conversion actions, not all buttons)
    if extraction.analysis and extraction.analysis.primaryCTAs:
        summary_parts.append("\n## Primary CTAs")
        for cta in extraction.analysis.primaryCTAs:
            summary_parts.append(f"- {cta}")
    elif extraction.summary.ctaClues:
        summary_parts.append("\n## CTA Buttons Found")
        for cta in extraction.summary.ctaClues[:5]:
            summary_parts.append(f"- {cta}")
    
    # NEW: Value proposition from analysis
    if extraction.analysis and extraction.analysis.valueProposition:
        summary_parts.append("\n## Value Proposition")
        summary_parts.append(extraction.analysis.valueProposition)

    # Brand assets (unchanged - these are fine)
    if extraction.brandAssetCues:
        summary_parts.append("\n## Brand Assets")
        colors = [c for c in extraction.brandAssetCues if c.assetType == "color"]
        if colors:
            summary_parts.append(f"Colors: {', '.join(c.value for c in colors[:3])}")

        logos = [c for c in extraction.brandAssetCues if c.assetType == "logo"]
        if logos:
            summary_parts.append(f"Logo: {logos[0].label}")

        fonts = [c for c in extraction.brandAssetCues if c.assetType == "typography"]
        if fonts:
            summary_parts.append(f"Typography: {fonts[0].value}")

    # Analysis confidence indicator
    if extraction.analysis and extraction.analysis.confidence > 0:
        summary_parts.append(f"\n## Analysis Confidence: {extraction.analysis.confidence}%")

    return "\n".join(summary_parts)
```

#### 2.2 Improve Master Brief Prompt

**File**: `apps/backend/app/core/master_brief.py`

Update `_build_initial_prompt` to emphasize using the analysis (lines 152-195):

```python
def _build_initial_prompt(extraction_summary: str) -> str:
    """Build the initial master brief generation prompt."""
    prompt = f"""You are a landing page strategist. Given the following ANALYZED data about a business, create a master brief for a high-converting landing page.

IMPORTANT: This data has been pre-analyzed by AI. The services, tone, and audience descriptions are already synthesized - use them as-is, don't try to re-interpret.

{extraction_summary}

## Constraints
- This is a SINGLE landing page (not a multi-page site)
- Keep all content concise - headlines under 8 words, descriptions under 2 sentences
- The page must have a clear conversion goal
- Choose 4-7 sections maximum
- Be specific about visual direction - not generic
- DO NOT generate empty or placeholder fields - every field must have real content

## Output Format
Return a JSON object with this structure:
{{
  "businessGoal": "What this landing page should achieve (specific, not generic)",
  "primaryAudience": "Who we're talking to (use the analyzed audience data)",
  "conversionAction": "The one thing we want them to do (use the primary CTA)",
  "valueProposition": "Why they should care (use analyzed value prop, expand if needed)",
  "toneAndVoice": "How we sound (use the analyzed tone)",
  "visualStyle": "Description of look/feel (be specific, not 'clean and modern')",
  "colorStrategy": "How colors should be used (specific strategy)",
  "motionLevel": "none|subtle|moderate|dramatic",
  "specialEffects": ["3d-hero", "parallax-scroll"] or [],
  "headline": "Main hero headline (8 words max, compelling)",
  "subheadline": "Supporting line (2 sentences max)",
  "sections": [
    {{
      "purpose": "social-proof|services|process|cta|about|etc",
      "headline": "Section headline (clear, specific)",
      "contentSummary": "What goes in this section (detailed, not vague)",
      "suggestedApproach": "testimonial carousel, bento grid, icon list, etc",
      "contentPoints": ["key point 1 (specific)", "key point 2 (specific)", "key point 3"]
    }}
  ],
  "ctaStrategy": "Primary + secondary CTAs approach (be specific)",
  "aiReasoning": "Why these choices were made based on the analyzed data",
  "confidenceScore": 85
}}

CRITICAL: Every field must be populated with real, specific content. No empty arrays, no generic descriptions, no "TBD" placeholders.

Return ONLY valid JSON, no markdown formatting."""
    
    return prompt
```

#### 2.3 Test Phase 2

```bash
# Test master brief generation with new analysis data
cd apps/backend
python -m pytest tests/ -k master_brief -v

# Manual test:
# 1. Extract a site (should have analysis field)
# 2. Generate master brief
# 3. Verify brief has:
#    - Real tone (not "Primary logo")
#    - Service descriptions (not bare headings)
#    - Populated audience field
#    - Specific value proposition
```

---

### **PHASE 3: Delete Legacy Code** (1-2 hours)

**Goal**: Remove all keyword-based heuristics and legacy brief code. Keep codebase clean.

#### What Gets DELETED vs What STAYS

##### ❌ DELETE (LEGACY - No Longer Needed)

**Old Brief System** (~1000 lines):
- `create_brief()` - replaced by `create_master_brief()`
- `approve_brief()` - replaced by `approve_master_brief()`
- `update_brief()` - not needed (master brief regenerates)
- `get_brief()` - replaced by `get_master_brief()`
- `_build_brief_doc()` - deterministic brief builder (200+ lines)
- `_brief_source_references()` - brief helper methods
- `_brief_doc_to_snapshot()` - conversion methods
- `SiteBrief` schema (if exists) - replaced by `MasterBrief`

**Keyword Detection** (~500 lines):
- Extended CTA keyword list (31 keywords) → LLM analysis
- Tone keyword patterns ("professional", "friendly") → LLM analysis
- Service extraction from headings → LLM analysis
- Material Design icon filtering → Simplified logo detection
- `_looks_like_cta()` function → Deleted entirely

**Enrichment System** (entire file):
- `extraction_enrichment.py` - replaced by `extraction_analysis.py`
- `enrich_extraction()` - only ran when sparse (wrong logic)
- `_infer_services()` - moved to analysis
- `_infer_audience()` - moved to analysis
- `_infer_positioning()` - moved to analysis

**Total Deletion**: ~1500 lines of legacy code ✂️

##### ✅ KEEP (Core Functionality)

**Extraction Core** (simplified):
- `crawl_website()` - HTML/text collection (no analysis)
- `_safe_fetch()` - HTTP fetching
- `_parse_html()` - HTML parsing
- `PageSignals` - raw signal collection
- Basic logo detection (simplified, no complex filtering)
- Image/asset collection

**Master Brief System** (enhanced):
- `create_master_brief()` - AI-powered brief ✅
- `approve_master_brief()` - NEW in Phase 0 ✅
- `refine_master_brief()` - feedback loop ✅
- `get_master_brief()` - retrieval ✅
- `MasterBrief` schema - strategy model ✅
- `generate_master_brief()` - LLM generation ✅

**Analysis System** (NEW):
- `extraction_analysis.py` - semantic understanding ✨
- `analyze_extraction()` - LLM analysis ✨
- `ExtractionAnalysis` schema - analyzed data ✨

**Pipeline Flow** (fixed):
- `advance_pipeline_after_extraction()` - triggers analysis → brief
- `advance_pipeline_after_brief()` - triggers site generation
- Sequential execution (no parallel brief/site)

##### 🔄 MODIFY (Update to Use Analysis)

**Master Brief**:
- `_build_extraction_summary()` - use `analysis.services` not `serviceClues`

**Site Generation**:
- Read `master_brief` (not old `brief`)
- Use `extraction.analysis` for content

**API Routes**:
- Update endpoints to use master brief
- Deprecate or delete old brief routes

#### 3.1 DELETE Old Brief System Completely

**Goal**: Remove ALL traces of the old deterministic brief system. Only master brief should exist.

##### 3.1.1 Find All Old Brief Code

```bash
cd apps/backend

# Search for old brief references
grep -r "create_brief\|approve_brief\|_build_brief_doc\|SiteBrief" \
  --include="*.py" app/ | grep -v "master_brief" | grep -v "test"

# Should find in leads.py:
# - create_brief() method (line ~2564)
# - approve_brief() method
# - _build_brief_doc() method (line ~1904)
# - update_brief() method
# - get_brief() method
```

##### 3.1.2 DELETE Methods from leads.py

**File**: `apps/backend/app/core/leads.py`

**DELETE THESE ENTIRE METHODS**:

1. **`create_brief()`** (line ~2564-2590)
   ```python
   # DELETE FROM HERE:
   async def create_brief(self, lead_id: str) -> SiteBrief | None:
       # ... entire method ...
   # TO HERE (end of method)
   ```

2. **`_build_brief_doc()`** (line ~1904-2100)
   ```python
   # DELETE FROM HERE:
   def _build_brief_doc(
       self,
       *,
       lead: LeadDetail,
       extraction: ExtractionSnapshot,
       # ... entire method (200+ lines) ...
   # TO HERE
   ```

3. **`approve_brief()`** (find with grep)
   ```python
   # DELETE ENTIRE METHOD:
   async def approve_brief(self, lead_id: str, approved_by: str) -> SiteBrief | None:
       # ... entire method ...
   ```

4. **`update_brief()`** (line ~2592)
   ```python
   # DELETE ENTIRE METHOD:
   async def update_brief(
       self,
       lead_id: str,
       patch: SiteBriefPatchRequest,
       # ... entire method ...
   ```

5. **`get_brief()`** (find with grep)
   ```python
   # DELETE ENTIRE METHOD:
   async def get_brief(self, lead_id: str) -> SiteBrief | None:
       # ... entire method ...
   ```

6. **`_latest_brief_doc()`** (find with grep)
   ```python
   # DELETE ENTIRE METHOD:
   async def _latest_brief_doc(self, lead_id: str) -> dict[str, Any] | None:
       # ... entire method ...
   ```

7. **`_brief_doc_to_snapshot()`** (find with grep)
   ```python
   # DELETE ENTIRE METHOD:
   def _brief_doc_to_snapshot(self, doc: dict[str, Any]) -> SiteBrief:
       # ... entire method ...
   ```

8. **`_brief_source_references()`** (line ~1923 or nearby)
   ```python
   # DELETE ENTIRE METHOD:
   def _brief_source_references(
       self, *, extraction: ExtractionSnapshot, asset_cues: list
   ) -> list[BriefSourceReference]:
       # ... entire method ...
   ```

**Total deletion**: ~800-1000 lines of legacy brief code

##### 3.1.3 Update API Routes

**File**: `apps/backend/app/api/leads.py`

**FIND** routes that reference old brief:
```bash
grep -n "create_brief\|approve_brief\|update_brief\|get_brief" apps/backend/app/api/leads.py
```

**DELETE or REPLACE**:

```python
# OLD ROUTE (DELETE THIS):
@router.post("/{lead_id}/brief", response_model=SiteBriefResponse)
async def create_brief_route(lead_id: str, user_id: str = Depends(require_auth)):
    brief = await lead_repository.create_brief(lead_id)
    return {"brief": brief}

# If needed, redirect to master brief:
@router.post("/{lead_id}/brief", response_model=MasterBriefResponse)
async def create_brief_route(lead_id: str, user_id: str = Depends(require_auth)):
    """Legacy endpoint - redirects to master brief."""
    master_brief = await lead_repository.create_master_brief(lead_id)
    return {"brief": master_brief}
```

**Or just DELETE the routes entirely** if frontend already uses master brief endpoints.

##### 3.1.4 Delete Old Brief Schema

**File**: `apps/backend/app/schemas/brief.py`

Check if `SiteBrief` model still exists:

```python
# If this exists, DELETE IT:
class SiteBrief(BaseModel):
    id: str
    leadId: str
    # ... old brief fields ...
```

**Keep only**: `MasterBrief`, `MasterBriefSection`, `BrandAssets`

##### 3.1.5 Update Site Generation

**File**: `apps/backend/app/core/sites.py`

**FIND** any references to old brief:
```bash
grep -n "SiteBrief\|get_brief\|\.brief\." apps/backend/app/core/sites.py
```

**REPLACE ALL** with master brief:
```python
# OLD:
brief = await lead_repository.get_brief(lead_id)

# NEW:
master_brief = await lead_repository.get_master_brief(lead_id)
if master_brief is None:
    raise ValueError("no_master_brief_for_generation")
```

##### 3.1.6 Clean Up Database Collection (Optional)

**MongoDB**: The old `site_briefs` collection can be archived:

```javascript
// In MongoDB shell:
// Rename old collection to archive
db.site_briefs.renameCollection("site_briefs_archive_2026");

// Or just leave it - it won't hurt anything
// New code only reads from master_briefs collection
```

**Don't delete data** - keep archive for reference/debugging.

##### 3.1.7 Update Frontend (if needed)

Check if frontend has any references to old brief:

```bash
cd apps/web
grep -r "SiteBrief\|/brief" src/ --include="*.ts" --include="*.tsx"
```

**Replace** any old brief API calls with master brief calls:
```typescript
// OLD:
const response = await apiClient.post(`/leads/${leadId}/brief`);

// NEW:
const response = await apiClient.post(`/leads/${leadId}/master-brief`);
```

##### 3.1.8 Verification Checklist

After deletion, verify:

```bash
# Should return ZERO results (except in tests/archives):
cd apps/backend
grep -r "create_brief\|_build_brief_doc\|SiteBrief" app/ \
  | grep -v "master_brief" \
  | grep -v "test" \
  | grep -v "archive"

# If any results found, delete those references too
```

**Zero tolerance for legacy code** - if grep finds it, delete it.

#### 3.2 Code to DELETE from `extraction.py`

**File**: `apps/backend/app/core/extraction.py`

**DELETE Lines 1570-1605** (Keyword-based tone detection):

```python
# DELETE THIS ENTIRE BLOCK:
            # Enhanced tone detection from actual content
            all_text = " ".join(signals.body_text[:50]).lower()

            # Professional/formal tone indicators
            if any(word in all_text for word in ["we provide", "our services", ...]):
                tone_clues.append("Professional/formal tone with emphasis on expertise and credentials")

            # Friendly/conversational tone indicators
            if any(word in all_text for word in ["we're here", "let's", ...]):
                tone_clues.append("Friendly/conversational tone with welcoming language")

            # ... (delete all keyword-based tone detection)
```

**DELETE Lines 1543-1668** (Keyword-based service extraction):

```python
# DELETE THIS ENTIRE BLOCK:
            # Enhanced service extraction - prioritize actual descriptions over bare headings
            for section in page_data.get("sections", []):
                section_type = section.get("type")
                section_text = section.get("text") or ""
                heading = section.get("heading")

                # For services sections, extract service descriptions
                if section_type == "services":
                    # ... (delete all keyword-based service extraction)
```

**DELETE Lines 494-533** (Extended CTA keyword list):

**DELETE the entire function** - LLM analysis will extract CTAs instead:

```python
# DELETE THIS ENTIRE FUNCTION:
def _looks_like_cta(text: str) -> bool:
    lowered = text.lower()
    return any(
        keyword in lowered
        for keyword in [...]  # ALL OF THIS - DELETE
    )
```

**WHY**: 
- CTA detection via keywords is language-specific (English only)
- LLM analysis (Phase 1) will extract primary CTAs from all button/link text
- No need for heuristics - raw extraction just collects ALL buttons/links
- Analysis layer decides which are actual conversion CTAs

**Replace usage** in extraction:
```python
# OLD (line ~405):
if self._text_target == "cta" or _looks_like_cta(text):
    self.signals.ctas.append(text)

# NEW (simplified - collect everything, let analysis filter):
if self._text_target == "cta":
    self.signals.ctas.append(text)
# No keyword filtering - analysis will pick primary CTAs later
```

**DELETE Lines 320-390** (Logo detection filtering):

Simplify logo detection - we don't need perfect logo detection at extraction time:

```python
# REPLACE the complex filtering with simple detection:
            # Simple logo detection - capture all candidates
            hint = f"{alt} {title} {src} {class_attr} {id_attr}".lower()
            if "logo" in hint or "/logo" in src.lower():
                self.signals.logo_candidates.append(candidate or src.strip())
```

#### 3.3 Code to DELETE from `extraction_enrichment.py`

**File**: `apps/backend/app/core/extraction_enrichment.py`

**OPTION A**: Delete entire file (if not used elsewhere)
**OPTION B**: Keep for backwards compatibility but deprecate:

Add deprecation notice at top:

```python
"""
DEPRECATED: This module is being phased out.
Use extraction_analysis.py instead for LLM-based semantic analysis.

This module only runs when extraction is sparse AND analysis is not present.
"""

import warnings
warnings.warn(
    "extraction_enrichment is deprecated, use extraction_analysis instead",
    DeprecationWarning,
    stacklevel=2
)
```

#### 3.4 Update Extraction Job to Skip Enrichment

**File**: `apps/backend/app/core/leads.py`

**DELETE or COMMENT OUT** the enrichment step (lines 3011-3031):

```python
# DELETE THIS BLOCK (or comment out):
    # Phase 1: Validate + LLM-enrich extraction if content is sparse
    is_valid, content_issues = validate_extraction_content(crawl_data)
    if not is_valid:
        logging.getLogger("lenquant.jobs").info(
            "Extraction content sparse for %s: %s — running LLM enrichment",
            lead_id,
            content_issues,
        )
        await self._update_job(
            job_id,
            progress=60,
            step="Enriching extraction with LLM analysis",
            lead_ids=[lead_id],
        )
        try:
            await enrich_extraction(crawl_data)
        except Exception as enrich_err:
            logging.getLogger("lenquant.jobs").warning(
                "LLM enrichment failed: %s", enrich_err
            )

# REPLACE WITH COMMENT:
    # Extraction analysis now happens in Phase 2 (see below)
    # Old enrichment logic removed - analysis always runs via extraction_analysis.py
```

#### 3.5 Search and Destroy: Legacy References

Run these commands to find and remove legacy references:

```bash
cd apps/backend

# Find any references to old brief types
grep -r "SiteBrief" --include="*.py" app/
grep -r "LegacyBrief" --include="*.py" app/
grep -r "site_brief" --include="*.py" app/

# Find any remaining keyword-based detection
grep -r "serviceClues" --include="*.py" app/ | grep -v "schema" | grep -v "test"
grep -r "toneClues" --include="*.py" app/ | grep -v "schema" | grep -v "test"

# Review each result and either:
# 1. Update to use extraction.analysis.services instead of serviceClues
# 2. Update to use extraction.analysis.tone instead of toneClues
# 3. Delete if no longer needed
```

#### 3.6 Update Documentation

**File**: `CLAUDE.md`

Add section about extraction architecture:

```markdown
## Extraction & Analysis Architecture

### Three-Layer System

1. **Extraction** (`app/core/extraction.py`)
   - Raw HTML/text crawling
   - Basic signal collection (images, links, headings)
   - NO semantic analysis
   - Fast, language-agnostic

2. **Analysis** (`app/core/extraction_analysis.py`)
   - LLM-powered semantic understanding
   - Detects: services, tone, CTAs, audience, positioning
   - Runs for ALL extractions (not just sparse ones)
   - Language-agnostic (works in any language)

3. **Master Brief** (`app/core/master_brief.py`)
   - Strategic synthesis for landing page
   - Uses analyzed data (not raw extraction)
   - Generates: headlines, sections, visual strategy

### Data Flow

```
Website → Extraction (raw HTML) → Analysis (LLM semantics) → Master Brief (strategy) → Site Generation
```

### Key Fields

- `extraction.analysis.services` - Real service descriptions
- `extraction.analysis.tone` - Synthesized voice (e.g., "Professional with friendly undertones")
- `extraction.analysis.primaryCTAs` - Main conversion actions
- `extraction.analysis.audience` - Target market description
- `extraction.analysis.valueProposition` - What makes them different
- `extraction.analysis.positioning` - 2-3 sentence summary

### Legacy Fields (Deprecated)

- ~~`extraction.summary.serviceClues`~~ - Use `analysis.services` instead
- ~~`extraction.summary.toneClues`~~ - Use `analysis.tone` instead
- ~~`extraction.summary.audienceClues`~~ - Use `analysis.audience` instead
```

---

## Testing Strategy

### Unit Tests

```bash
# Phase 1: Test analysis module
cd apps/backend
python -m pytest tests/test_extraction_analysis.py -v

# Phase 2: Test master brief with analysis
python -m pytest tests/test_master_brief.py -v

# Phase 3: Integration test full flow
python -m pytest tests/test_e2e_lenquant_flow.py -v
```

### Manual Testing Checklist

Create file: `EXTRACTION_TEST_CHECKLIST.md`

```markdown
# Extraction Analysis Testing Checklist

## Test Sites (Various Scenarios)

1. **English Professional Services**
   - URL: https://championwelldrilling.com
   - Expected: Professional tone, service descriptions, homeowner audience

2. **Spanish Site**
   - URL: [any Spanish business site]
   - Expected: Spanish services, Spanish tone description, proper analysis

3. **E-commerce**
   - URL: [any product site]
   - Expected: Product offerings as services, purchase CTAs

4. **SaaS**
   - URL: [any software site]
   - Expected: Software features as services, trial/demo CTAs

## What to Check

### Extraction Analysis (After Step 2)
- [ ] `analysis.services` has 3-8 real descriptions (not headings)
- [ ] `analysis.tone` is a sentence, not keywords
- [ ] `analysis.primaryCTAs` has 1-3 main actions (not all buttons)
- [ ] `analysis.audience` is populated (not empty)
- [ ] `analysis.valueProposition` is specific (not generic)
- [ ] `analysis.positioning` is 2-3 sentences (not raw meta tags)
- [ ] `analysis.confidence` is 50-95 (reasonable range)

### Master Brief (After Step 3)
- [ ] `businessGoal` is specific (not generic)
- [ ] `primaryAudience` uses analyzed audience
- [ ] `valueProposition` is populated (not empty)
- [ ] `toneAndVoice` uses analyzed tone (not "Primary logo")
- [ ] `sections` array has 4-7 items with real content
- [ ] Each section has populated `contentPoints` (not empty)
- [ ] `ctaStrategy` references actual CTAs from analysis

### Site Generation (After Step 4)
- [ ] Generated hero section reflects analyzed tone
- [ ] Services section uses analyzed service descriptions
- [ ] CTAs match primary CTAs from analysis
- [ ] Overall page feels cohesive with analysis insights

## Regression Tests

- [ ] Old extractions (without analysis) still work
- [ ] Master brief falls back gracefully if analysis missing
- [ ] Site generation works with both analyzed and legacy data
```

---

## Rollout Plan

### Pre-Launch

1. **Code Review**
   - Review all new code in `extraction_analysis.py`
   - Review all changes to `master_brief.py`
   - Verify all deletions are safe

2. **Staging Deployment**
   - Deploy to staging environment
   - Run full test suite
   - Manual test with 10+ different sites

3. **Performance Testing**
   - Measure LLM call latency (expect +2-5 seconds per extraction)
   - Check cost impact (~$0.01-0.05 per extraction)
   - Verify no memory issues

### Launch

1. **Deploy Phase 1** (Day 1)
   - Deploy analysis module
   - Monitor: extractions should have `analysis` field
   - Monitor: no errors in logs

2. **Deploy Phase 2** (Day 2-3)
   - Deploy master brief changes
   - Monitor: briefs should have populated fields
   - Monitor: quality of generated sites

3. **Deploy Phase 3** (Day 4-5)
   - Delete legacy code
   - Monitor: no breakage from deletions
   - Final cleanup

### Post-Launch

1. **Quality Metrics**
   - Track: % of briefs with populated audience field
   - Track: % of briefs with populated sections
   - Track: average `analysis.confidence` score

2. **Cost Tracking**
   - Monitor: LLM tokens used per extraction
   - Calculate: cost per lead vs quality improvement

3. **Iteration**
   - Collect feedback on analysis quality
   - Tune analysis prompt based on results
   - Adjust confidence thresholds

---

## Success Criteria

### Quantitative

- ✅ 95%+ of master briefs have populated audience field (vs <10% before)
- ✅ 95%+ of master briefs have populated section content (vs <50% before)
- ✅ 0 instances of "Primary logo" in tone field (vs ~30% before)
- ✅ Average analysis confidence ≥ 70
- ✅ All tests passing
- ✅ No increase in extraction failure rate

### Qualitative

- ✅ Tone descriptions read naturally (not keyword salad)
- ✅ Service listings are actual offerings (not "Services", "About")
- ✅ Master briefs feel specific to the business (not generic)
- ✅ Generated sites match the business's actual voice
- ✅ Works in multiple languages (Spanish, French, etc.)

---

## Rollback Plan

If critical issues found post-launch:

1. **Immediate**: Disable analysis step
   ```python
   # In leads.py, comment out analysis call:
   # analysis_result = await analyze_extraction(temp_snapshot)
   # Use empty analysis instead:
   crawl_data["analysis"] = _empty_analysis()
   ```

2. **Short-term**: Master brief falls back to keyword data
   - Already built into Phase 2 implementation
   - Brief will use `serviceClues` if `analysis.services` empty

3. **Restore**: Re-enable enrichment if needed
   ```python
   # Uncomment enrichment step in leads.py
   if not is_valid:
       await enrich_extraction(crawl_data)
   ```

---

## Cost Analysis

### Current (Keyword-Based)

- Extraction: ~$0.00 (pure code)
- Enrichment: ~$0.01-0.02 (only if sparse, ~20% of extractions)
- Master Brief: ~$0.03-0.05
- **Total: ~$0.03-0.07 per lead**

### New (LLM Analysis)

- Extraction: ~$0.00 (pure code, simplified)
- Analysis: ~$0.02-0.05 (always runs, better prompts)
- Master Brief: ~$0.03-0.05 (cleaner inputs, fewer retries)
- **Total: ~$0.05-0.10 per lead**

### ROI

- Cost increase: +$0.02-0.03 per lead (~50% increase)
- Quality improvement: 3-5x (based on populated fields metric)
- Fewer regenerations: -30% (better briefs = fewer "try again")
- **Net: Better quality at slightly higher cost, but saves on regenerations**

---

## Timeline

| Phase | Duration | Tasks |
|-------|----------|-------|
| **Phase 0** | **30 mins** | **Fix auto pipeline to use master brief, add approval method, ensure sequential execution** |
| Phase 1 | 2-3 hours | Create analysis module, update schema, integrate into extraction job |
| Testing | 1 hour | Unit tests, manual tests on 5+ sites |
| Phase 2 | 1-2 hours | Update master brief to use analysis data |
| Testing | 1 hour | Verify briefs have populated fields |
| Phase 3 | 1-2 hours | Delete legacy code, clean up references |
| Testing | 1 hour | Regression tests, verify no breakage |
| Documentation | 1 hour | Update CLAUDE.md, add inline comments |
| **Total** | **8.5-11.5 hours** | **Full implementation + testing** |

---

## Schema Requirements

### MasterBrief Must Have Approval Fields

**File**: `apps/backend/app/schemas/brief.py`

Verify `MasterBrief` model has these fields:

```python
class MasterBrief(BaseModel):
    id: str
    leadId: str
    version: int
    
    # ... existing strategy fields ...
    
    # REQUIRED: Approval state tracking
    approvalState: str = "pending"  # "pending" | "approved" | "rejected"
    approvedBy: str | None = None
    approvedAt: datetime | None = None
    approvalNotes: str | None = None
    
    createdAt: datetime
    updatedAt: datetime
```

If missing, add them. The auto pipeline needs these to track approval.

---

## Dependencies

- ✅ LLM client (`app.core.llm`) - already exists
- ✅ Extraction schemas (`app.schemas.extraction`) - exists, need to extend
- ✅ Master brief module (`app.core.master_brief`) - exists, need to update
- ✅ Master brief schema (`app.schemas.brief`) - exists, verify approval fields
- ✅ Extraction job (`app.core.leads.run_extraction_job`) - exists, need to update
- ✅ Site generation (`app.core.sites`) - exists, need to use master brief

No new external dependencies required.

---

## Questions for Team

1. **Cost approval**: +$0.02-0.03 per extraction acceptable?
2. **Rollout speed**: All 3 phases at once, or phase-by-phase over 1 week?
3. **Analysis retention**: Keep analysis in DB permanently, or only for recent extractions?
4. **Backwards compatibility**: Support old extractions without analysis for how long?
5. **Manual override**: Allow operators to edit analysis results before master brief?

---

## Contact

For questions or issues during implementation:
- Primary: Check `CLAUDE.md` for architecture reference
- Logs: `apps/backend/logs/` for extraction/analysis errors
- Database: `site_extractions` collection has analysis field
- Slack: #lenquant-dev for team discussion

---

**Ready to implement?** Start with Phase 1 and verify each phase before moving to the next.
