# Site Generation Issues & Fix Strategy

**Date:** 2026-07-15  
**Context:** Comprehensive audit of Stripe site generation revealing critical bugs in extraction, briefing, and rendering pipeline.

---

## Executive Summary

The site generation is producing low-quality output due to **5 critical system failures**:

1. **Extraction captures metadata but misses content** - 80 sections found but 0 services extracted
2. **Visual redesign returns invalid component IDs** - Pydantic class names instead of React component IDs
3. **No content validation/enrichment** - Empty data passes through to rendering
4. **Technical terms leak to public site** - "Brand cues", "Conversion path" visible to visitors
5. **Multiple structural errors** - CTA malformation, slug generation, quality validation

**Current State:** Site shows "Unknown" sections, no menu, poor content, 0/100 quality score

---

## PHASE 1: EXTRACTION & CONTENT CAPTURE (Critical - Blocks Everything)

### Issue 1.1: Services/Offerings Not Being Extracted
**Severity:** 🔴 Critical  
**Current State:**
- Extraction finds 80 sections from Stripe
- `serviceClues` array returns **EMPTY** (0 items)
- `audienceClues` returns only 1 item
- 95% confidence score is misleading - metadata extraction works, content extraction fails

**Why This Happens:**
- Extraction logic likely relies on specific HTML patterns or keywords
- Stripe's modern SPA structure may not match expected patterns
- Section detection works, but semantic parsing (services, audience) fails
- LLM is not analyzing section *content* to infer services

**Impact:**
- Sections have no content to populate
- Brief generation has no service data to work with
- Section titles default to "Unknown" or "Services or Offerings" (generic)
- Site has no substance - just headings and empty cards

**Fix Required:**
```python
# In extraction.py or wherever serviceClues are extracted:

# CURRENT (broken):
serviceClues = extract_services_from_metadata(page)  # Returns []

# NEEDED:
if len(serviceClues) < 3:  # Threshold for "enough content"
    # Fallback: Use LLM to analyze actual extracted text
    serviceClues = await llm_analyze_services_from_sections(
        sections=sectionInventory,
        company_name=companyName,
        industry=detected_industry,
        min_required=3  # Don't proceed with < 3 services
    )
```

**Acceptance Criteria:**
- ✅ Extract at least 3-5 service/offering items from Stripe
- ✅ Services should be actual Stripe offerings: "Payment processing", "Billing management", "Fraud detection", etc.
- ✅ If extraction fails, LLM analyzes section text (min 1000 words) to infer services
- ✅ If total extracted content < 1000 words, flag for manual review (don't hallucinate)

---

### Issue 1.2: Content vs Metadata Balance
**Severity:** 🔴 Critical  
**Current State:**
- System extracts structure (80 sections) but not substance
- Citations exist (88) but content fields are sparse
- No validation that extracted data has enough *usable content*

**Why This Happens:**
- Extraction prioritizes structure over content
- No minimum content threshold before proceeding
- System assumes extraction success if metadata populates

**Impact:**
- Brief and site generation work with hollow data
- Results in generic, templated output with no specificity
- Can't differentiate between "extraction worked" and "extraction got metadata only"

**Fix Required:**
```python
# After extraction completes, validate content quality:

def validate_extraction_content(extraction: ExtractionSnapshot) -> tuple[bool, list[str]]:
    """
    Validate extracted content is sufficient for site generation.
    Returns (is_valid, missing_items)
    """
    issues = []
    
    # Count total extracted text
    total_text = sum(len(s.text or '') for s in extraction.sectionInventory)
    if total_text < 1000:
        issues.append(f"Only {total_text} chars extracted, need 1000+ for content generation")
    
    # Check critical data
    if len(extraction.summary.serviceClues) < 3:
        issues.append("Less than 3 services extracted")
    
    if len(extraction.summary.audienceClues) < 2:
        issues.append("Less than 2 audience signals extracted")
    
    if not extraction.summary.positioningSummary or len(extraction.summary.positioningSummary) < 50:
        issues.append("Positioning summary too short or missing")
    
    return (len(issues) == 0, issues)

# Before brief generation:
is_valid, issues = validate_extraction_content(extraction)
if not is_valid:
    # Option A: Enrich with LLM analysis of what WAS extracted
    # Option B: Flag for manual review
    # Option C: Reject and require re-extraction
    logger.warning(f"Extraction quality insufficient: {issues}")
```

**Acceptance Criteria:**
- ✅ Validate extraction has min 1000 words of content
- ✅ Validate min 3 services, 2 audience clues, positioning summary
- ✅ If validation fails, attempt LLM enrichment from extracted text
- ✅ If enrichment fails, reject generation (don't hallucinate)

---

### Issue 1.3: No Fallback Content Generation
**Severity:** 🟡 Medium  
**Current State:**
- When extraction misses content, system proceeds with empty data
- No attempt to generate reasonable content from partial data
- LLM is never asked to "fill in gaps" based on what WAS extracted

**Fix Required:**
```python
async def enrich_sparse_extraction(
    extraction: ExtractionSnapshot,
    llm: LLMClient
) -> ExtractionSnapshot:
    """
    When extraction is sparse, use LLM to infer missing data from what we have.
    Only use if we have 1000+ words to work from - otherwise risk hallucination.
    """
    total_content = sum(len(s.text or '') for s in extraction.sectionInventory)
    
    if total_content < 1000:
        raise ValueError("Not enough content to safely enrich (< 1000 words)")
    
    # If services empty, infer from section text
    if len(extraction.summary.serviceClues) < 3:
        services = await llm.analyze_services(
            company=extraction.summary.companyName,
            sections=[s.text for s in extraction.sectionInventory],
            instruction="Based ONLY on the text provided, identify 3-5 services/offerings. Do not invent."
        )
        extraction.summary.serviceClues = services
    
    # If audience empty, infer from content
    if len(extraction.summary.audienceClues) < 2:
        audience = await llm.analyze_audience(...)
        extraction.summary.audienceClues = audience
    
    return extraction
```

**Acceptance Criteria:**
- ✅ Only enrich if we have 1000+ words of extracted content
- ✅ LLM instructed explicitly: "Based ONLY on provided text, do not invent"
- ✅ Enrichment logged as "inferred" vs "extracted" for traceability

---

## PHASE 2: BRIEFING & COMPONENT SELECTION (Blocks Quality Output)

### Issue 2.1: Visual Redesign Returns Invalid Component IDs
**Severity:** 🔴 Critical  
**Current State:**
```python
# What we're getting:
critique.recommendedComponent = "SectionStandard"  # Pydantic class name
critique.recommendedComponent = "HeroSplitEditorial"  # Wrong format

# What we need:
critique.recommendedComponent = "services-bento"  # React component ID
critique.recommendedComponent = "hero-split-editorial"  # Kebab-case
```

**Why This Happens:**
- Visual redesign LLM prompt likely includes Pydantic schema definitions
- LLM returns schema class names instead of component IDs
- No validation that returned component ID exists in `PREMIUM_COMPONENTS` registry

**Impact:**
- Frontend `getPremiumComponent()` returns `null`
- Sections render as "Unknown" 
- No premium components shown
- Defeats entire visual redesign system

**Fix Required:**
```python
# In visual_redesign.py, after LLM response:

VALID_COMPONENT_IDS = {
    "hero-split-editorial",
    "hero-centered",
    "video-hero",
    "services-bento",
    "services-tabs",
    "services-accordion",
    "proof-carousel",
    "proof-grid-interactive",
    "timeline-vertical",
    "gallery-masonry",
    "stats-counter",
    "features-comparison",
    "cta-banner",
    "cta-sticky",
}

def validate_and_fix_component_id(component_id: str) -> str:
    """
    Validate component ID and fix common errors.
    """
    # Already valid
    if component_id in VALID_COMPONENT_IDS:
        return component_id
    
    # Try converting PascalCase to kebab-case
    # "HeroSplitEditorial" -> "hero-split-editorial"
    kebab = re.sub(r'(?<!^)(?=[A-Z])', '-', component_id).lower()
    if kebab in VALID_COMPONENT_IDS:
        logger.warning(f"Fixed component ID: {component_id} -> {kebab}")
        return kebab
    
    # "SectionStandard" -> fallback to section type
    logger.error(f"Invalid component ID: {component_id}, using fallback")
    return "services-bento"  # Safe default

# Apply after LLM extraction:
critique.recommendedComponent = validate_and_fix_component_id(
    data.get("recommendedComponent")
)
```

**LLM Prompt Fix:**
```python
# In visual redesign prompt, be explicit:

AVAILABLE_COMPONENTS:
hero-split-editorial (NOT HeroSplitEditorial)
services-bento (NOT ServicesBento or SectionStandard)
proof-carousel (NOT ProofCarousel)
...

Return ONLY the kebab-case component ID. Example: "services-tabs"
```

**Acceptance Criteria:**
- ✅ All component IDs returned are valid kebab-case React component IDs
- ✅ Validation rejects/fixes Pydantic class names
- ✅ LLM prompt explicitly shows correct format with examples
- ✅ Fallback to safe default if validation fails

---

### Issue 2.2: Technical Terms Leak to Public Site
**Severity:** 🟡 Medium (UX Issue)  
**Current State:**
- Section titles: "Brand cues", "Conversion path", "Open questions"
- These are operator/internal terminology
- Visible on public preview site

**Why This Happens:**
- Brief generation uses internal field names as section titles
- Sanitization exists but doesn't catch all cases
- No final validation that public-facing text is client-safe

**Impact:**
- Unprofessional appearance
- Exposes internal process to customers
- Confusing for site visitors

**Fix Required:**
```python
INTERNAL_TO_PUBLIC_SECTION_TITLES = {
    "brand cues": "About",
    "conversion path": "Contact",
    "cta pattern": "Get Started",
    "open questions": None,  # Drop entirely
    "missing requirements": None,  # Drop entirely
    "gap items": None,  # Drop entirely
}

def sanitize_section_title(title: str) -> str | None:
    """
    Convert internal section titles to public-friendly versions.
    Returns None if section should be dropped.
    """
    lowered = title.lower().strip()
    
    # Check direct mappings
    if lowered in INTERNAL_TO_PUBLIC_SECTION_TITLES:
        return INTERNAL_TO_PUBLIC_SECTION_TITLES[lowered]
    
    # Drop if contains operator terms
    operator_terms = [
        "operator", "admin", "review", "gap", "missing",
        "requirements", "questions", "cues", "extraction"
    ]
    if any(term in lowered for term in operator_terms):
        return None
    
    # Capitalize properly
    return title.title()

# Apply in section generation before creating SiteSection:
for section in sections:
    clean_title = sanitize_section_title(section.title)
    if clean_title is None:
        continue  # Skip this section
    section.title = clean_title
```

**Acceptance Criteria:**
- ✅ No internal terms visible on public site
- ✅ Section titles are visitor-friendly: "Services", "About", "Contact", etc.
- ✅ Sections with only internal terms are dropped, not shown

---

### Issue 2.3: "Unknown" Section Titles
**Severity:** 🟡 Medium  
**Current State:**
- Multiple sections render with title "Unknown"
- Frontend shows "Unknown" when section has no title or invalid data

**Why This Happens:**
- Section created without title
- Title is empty string
- Frontend fallback is literal "Unknown"

**Fix Required:**
```python
# In section generation:
def ensure_section_title(section: dict, section_type: str, index: int) -> str:
    """
    Ensure every section has a reasonable title.
    """
    if section.get("title") and section["title"].strip():
        return section["title"]
    
    # Fallback based on section type
    type_titles = {
        "services": "Our Services",
        "proof": "Results",
        "about": "About",
        "contact": "Get in Touch",
        "cta": "Next Steps",
        "pricing": "Pricing",
        "process": "How It Works",
    }
    
    return type_titles.get(section_type, f"Section {index + 1}")

# Frontend fallback also needs improvement:
// In page.tsx:
const sectionTitle = section.headline || section.title || 
    getSectionTypeTitle(section.kind) || `Section ${index + 1}`;
```

**Acceptance Criteria:**
- ✅ No section shows "Unknown" text
- ✅ All sections have meaningful fallback titles
- ✅ Titles based on section type when actual title missing

---

## PHASE 3: RENDERING & POLISH (Quality & UX)

### Issue 3.1: CTA Structure Errors
**Severity:** 🟡 Medium  
**Current State:**
```
LLM rewriting failed: 'primaryCta', falling back to template-based generation
```

**Why This Happens:**
- Code expects `cta.primaryCta` structure
- Data has different structure (maybe `cta.primary.label`?)
- Mismatch between schema and actual data

**Fix Required:**
```python
# Debug what structure we're actually getting:
logger.debug(f"CTA structure: {type(cta)}, keys: {cta.keys() if isinstance(cta, dict) else 'N/A'}")

# Add defensive access:
def safe_get_cta_label(cta: Any) -> str:
    """Safely extract CTA label from various structures."""
    if isinstance(cta, str):
        return cta
    if isinstance(cta, dict):
        # Try various paths
        if "primaryCta" in cta:
            return cta["primaryCta"]
        if "primary" in cta:
            primary = cta["primary"]
            if isinstance(primary, dict) and "label" in primary:
                return primary["label"]
            return str(primary)
        if "label" in cta:
            return cta["label"]
    return "Learn more"  # Safe fallback
```

**Acceptance Criteria:**
- ✅ No `'primaryCta'` KeyError crashes
- ✅ CTAs extract properly regardless of structure
- ✅ Safe fallbacks when CTA data malformed

---

### Issue 3.2: Friendly Slugs Not Generating
**Severity:** 🟢 Low (UX Polish)  
**Current State:**
- URLs are UUIDs: `/sites/49e664f0f304438babcf8ea7ae1b8ae4`
- Should be: `/sites/stripe`

**Why This Happens:**
- Friendly slug code added but not executing
- May be silently failing
- Need to debug slug generation

**Fix Required:**
```python
# Add logging to slug generation:
logger.info(f"Generating friendly slug from: {company_name}")
friendly_slug = _generate_friendly_slug(company_name, existing_slugs)
logger.info(f"Generated slug: {friendly_slug}")

# Ensure it's being used:
previewSlug = friendly_slug  # Not site_id!
```

**Acceptance Criteria:**
- ✅ Stripe generates slug "stripe"
- ✅ Duplicates get numbered: "stripe2", "stripe3"
- ✅ Max 8 characters
- ✅ Logs show slug generation happening

---

### Issue 3.3: Quality Score Always 0
**Severity:** 🟡 Medium  
**Current State:**
```
Repeated sections detected. Returning quality score of 0.
```

**Why This Happens:**
- Validation detects duplicate section titles
- Sets quality to 0 as "hard failure"
- May be too strict OR sections actually are duplicated

**Fix Required:**
```python
# Make validation more lenient OR fix duplication:

# Option A: Only fail if MANY sections repeated
section_titles = [s.title for s in sections]
unique_ratio = len(set(section_titles)) / len(section_titles)
if unique_ratio < 0.6:  # 60% must be unique
    logger.warning("Too many repeated sections")
    quality_score = 0
else:
    quality_score = calculate_normal_quality(...)

# Option B: Fix root cause - why are sections duplicating?
# Check if visual redesign is creating multiple sections with same title
```

**Acceptance Criteria:**
- ✅ Quality score reflects actual quality, not validation artifacts
- ✅ Minor duplication doesn't force score to 0
- ✅ Major duplication (>40% repeated) still flags as issue

---

### Issue 3.4: No Navigation Menu
**Severity:** 🟡 Medium  
**Current State:**
- Site has no top navigation
- Sections not linked
- Single-page layout with no structure

**Why This Happens:**
- Navigation generation exists but may not be applying
- Frontend may not be rendering navigation data
- Component may be missing

**Fix Required:**
```python
# Verify navigation is generated:
navigation_config = generate_navigation(
    sections=sections,
    company_name=company_name,
    theme=theme
)

# Ensure it's in site data:
site.navigationConfig = navigation_config

# Frontend must render it:
// In page.tsx, add navigation component
{site.navigationConfig && (
    <Navigation items={site.navigationConfig.items} />
)}
```

**Acceptance Criteria:**
- ✅ Navigation menu visible at top
- ✅ Links to each major section
- ✅ Sticky/fixed on scroll
- ✅ Responsive on mobile

---

### Issue 3.5: No Animations/Interactions
**Severity:** 🟢 Low (Polish)  
**Current State:**
- Site is static
- No hover effects
- No scroll animations
- Premium components not showing interactivity

**Why This Happens:**
- Components selected but not rendering
- Animation classes not applying
- May need to verify premium components are actually being used

**Fix Required:**
```typescript
// Verify premium component is rendering:
const PremiumComponent = getPremiumComponent(section.componentId);
console.log('Component for', section.componentId, ':', PremiumComponent?.name);

if (!PremiumComponent) {
    // Fallback is rendering instead
    console.warn('No premium component found, using fallback');
}
```

**Acceptance Criteria:**
- ✅ Premium components render (not fallbacks)
- ✅ Hover effects work on cards/buttons
- ✅ Scroll-triggered animations fire
- ✅ Interactive elements respond to user input

---

## PHASE SUMMARY

### Phase 1: Content Foundation (Must Fix First)
1. ✅ Extract services properly (min 3-5)
2. ✅ Validate content quality (min 1000 words)
3. ✅ LLM enrichment fallback (if enough content exists)
4. ✅ Reject if < 1000 words (don't hallucinate)

**Why First:** Without content, nothing else matters. Brief and site will be hollow.

### Phase 2: Component Pipeline (Unblock Quality)
1. ✅ Fix visual redesign component IDs (kebab-case)
2. ✅ Sanitize technical terms from public text
3. ✅ Eliminate "Unknown" sections
4. ✅ Fix CTA structure errors

**Why Second:** With content, we need proper component selection and clean text.

### Phase 3: Polish & UX (Final Quality)
1. ✅ Friendly URLs
2. ✅ Quality score calculation
3. ✅ Navigation menu
4. ✅ Animations/interactions

**Why Third:** These are visible polish items that don't block core functionality.

---

## Implementation Priority

**Week 1 (Critical Path):**
- Day 1-2: Phase 1 (Extraction fixes)
- Day 3-4: Phase 2 (Component selection)
- Day 5: Phase 3 (Polish)

**Testing Checkpoints:**
- After Phase 1: Verify Stripe extraction shows 3+ services, 1000+ words
- After Phase 2: Verify site shows proper components, no "Unknown", no technical terms
- After Phase 3: Verify friendly URLs, quality score > 0, navigation works

---

## Root Cause Analysis: Why Did Stripe Extraction Fail?

### What Actually Happened:
1. ✅ **Structure detected:** 80 sections, 88 citations (95% confidence)
2. ❌ **Content missed:** 0 services, 1 audience clue
3. ❌ **Semantic analysis failed:** Couldn't parse "what Stripe does"

### Why Structure Worked But Content Failed:

**Theory 1: Pattern-Based Extraction**
- Extraction relies on HTML patterns (headings, lists, specific classes)
- Stripe's modern React SPA doesn't match legacy patterns
- Structure detection works (finds sections by layout)
- Content detection fails (doesn't understand semantic meaning)

**Theory 2: Keyword Matching**
- `serviceClues` extraction looks for keywords: "services", "offerings", "solutions"
- Stripe uses different terminology: "products", "platforms", "tools"
- Pattern doesn't match → array stays empty

**Theory 3: LLM Not Used for Content**
- Extraction uses LLM for structure but NOT for semantic analysis
- LLM should be analyzing section text to infer: "This section describes payment processing → that's a service"
- Current code may only extract what's explicitly labeled

### Evidence:
```python
# What we got:
extraction.sectionInventory = 80 sections  # Structure ✅
extraction.summary.companyName = "Stripe"  # Metadata ✅
extraction.summary.serviceClues = []       # Content ❌
extraction.summary.audienceClues = [1]     # Content ❌

# This pattern suggests:
# - HTML parsing works
# - LLM is NOT analyzing section content for semantic meaning
```

### The Fix:
After structural extraction, **always** run semantic analysis:

```python
# CURRENT (broken):
serviceClues = extract_services_from_html(page)  # Pattern matching only

# NEEDED:
serviceClues = extract_services_from_html(page)
if len(serviceClues) < 3:
    # Fallback: Use LLM to analyze actual extracted text
    serviceClues = await llm_analyze_services(
        sections=sectionInventory,
        company_name=companyName
    )
```

LLM should read the 80 sections we DID extract and answer: "What services does this company offer?" Even if the word "services" never appears, LLM can infer from context.

---

## Next Steps

1. **Review this document** - Confirm phases and priorities
2. **Phase 1 implementation** - Start with extraction fixes
3. **Test with Stripe** - Verify each fix produces better output
4. **Phase 2 & 3** - Continue once content pipeline works

**Estimated effort:** 3-5 days full-time development + testing
