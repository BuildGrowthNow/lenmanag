# Phase 16 Implementation Prompt: Operator-Driven Redesign and Regeneration

**Start Date**: May 31, 2026
**Previous Phase**: Phase 15 (Complete ✅) - Premium preview delivery and screenshot-based QA
**Context**: Full production stack ready for operator feedback loop

## Phase 15 Context (Prerequisite Knowledge)

Before starting Phase 16, understand that Phase 15 has delivered:

### Backend Infrastructure
- `screenshot_analyzer.py` → Full Playwright + Gemini Vision integration
- `screenshot_comparator.py` → Real async QA implementation  
- `sites.py` → Screenshot QA integrated at progress 80-85%
- Database schema includes: `screenshotRefs`, `qualityScore`, `layoutHash`, `qaStatus`
- All tests passing (18 tests)

### Frontend
- `premium-sections.tsx` → 9 premium components (hero, services, proof, timeline, gallery, cta, editorial, etc.)
- `[slug]/page.tsx` → Quality badge, screenshot preview, premium component rendering
- `nsa/sites/[id]/page.tsx` → Visual QA Analysis card showing quality metrics

### Key Points
- Sites are generated with `componentId` mappings to premium components
- Quality scores (0-100) determine readiness: <50 blocked, 50-75 needs refinement, 75+ ready
- Screenshots captured and analyzed with Gemini Vision for design heuristics
- All persistence to MongoDB with versioning support

---

## Phase 16 Goal

Enable operators to iteratively refine and regenerate previews using natural-language prompts while maintaining brand integrity, extracting original content, and ensuring quality gates.

**Primary Objective**: Create a safe, traceable operator feedback loop where refinement prompts trigger intelligent redesign regeneration with full version control.

---

## Implementation Scope

### Backend Tasks (60% of work)

#### 1. Database Schema Extensions
**File**: `apps/backend/app/schemas/site.py`

Add to `GeneratedSiteVersion`:
```python
class RefinementPromptRecord(BaseModel):
    """Stores a single operator refinement prompt and its outcome"""
    id: str                           # UUID4
    submittedAt: datetime             # When operator submitted
    operatorId: str                   # User ID of operator
    promptText: str                   # The refinement request
    resultVersionId: str | None       # Version ID this prompt produced
    status: str                       # "pending" | "success" | "failed"
    qualityScore: int | None          # QA score of result (if success)
    failureReason: str | None         # Why it failed (if failed)
    notes: str | None                 # Operator notes/context

class GeneratedSiteVersion:
    # Existing fields...
    refinementPromptId: str | None    # Current version's originating prompt
    promptHistory: list[RefinementPromptRecord] = Field(default_factory=list)
    isManuallyRefined: bool = False   # True if from operator prompt
```

Add to `GeneratedSite`:
```python
class GeneratedSite:
    # Existing fields...
    refinementPromptId: str | None    # Latest prompt that produced this site
    promptHistory: list[RefinementPromptRecord] = Field(default_factory=list)
```

#### 2. Database Helper Functions
**File**: `apps/backend/app/core/sites.py`

Add methods to `SiteRepository`:
```python
async def submit_refinement_prompt(
    self,
    site_id: str,
    prompt_text: str,
    operator_id: str,
) -> str:
    """
    Store operator prompt and return prompt record ID.
    Does NOT trigger regeneration (caller does that).
    """
    # Create RefinementPromptRecord with status="pending"
    # Store in database
    # Return prompt_id

async def update_prompt_result(
    self,
    site_id: str,
    prompt_id: str,
    version_id: str,
    quality_score: int,
    status: "success" | "failed",
    failure_reason: str | None = None,
) -> None:
    """
    After regeneration completes, update prompt record with outcome.
    Links prompt to resulting version.
    """

async def get_prompt_history(
    self,
    site_id: str,
) -> list[RefinementPromptRecord]:
    """Return prompt history for a site."""
```

#### 3. Regeneration Endpoint
**File**: `apps/backend/app/api/sites.py`

Add route:
```python
@router.post("/sites/{site_id}/regenerate")
async def regenerate_site_with_prompt(
    site_id: str,
    payload: {
        "refinementPrompt": str,      # Operator's natural language request
        "force": bool = False,        # Override quality checks
        "operatorId": str,            # Who submitted this
    }
) -> {
    "siteId": str,
    "previewVersionId": str,
    "promptId": str,
    "status": "queued" | "in_progress",
    "message": str,
}
```

Logic:
1. Validate prompt is not empty and not > 500 chars
2. Block prompts requesting fake testimonials, unsupported claims
3. Store prompt record (status="pending")
4. If quality check fails (force=false), validate previous version quality >= 60
5. Dispatch background job: `regenerate_with_prompt_job(site_id, prompt_id, operator_id)`
6. Return queued response with prompt_id

#### 4. Regeneration Job Handler
**File**: `apps/backend/app/core/tasks.py` (new function) or `sites.py`

Add async function:
```python
async def regenerate_site_with_prompt(
    site_id: str,
    prompt_id: str,
    operator_id: str,
    job_id: str,
) -> dict:
    """
    Full regeneration workflow triggered by operator prompt.
    
    Process:
    1. Load current site, brief, extraction, brand tokens
    2. Use operator prompt to refine visual redesign brief
    3. Call Gemini to enhance brief with operator guidance
    4. Generate new site version (calls run_generation_job)
    5. Capture screenshots and run QA
    6. If quality >= 75 OR force=true: 
       - Update site record with new version
       - Update prompt record: status="success", link to version_id
       - Return success
    7. Else:
       - Update prompt record: status="failed", reason="quality_below_threshold"
       - Return failure with detailed message
    """
```

Key steps:
- Preserve `brandTokens`, `layoutHash`, original extraction
- Only refine: component selection, section title/order, CTA wording
- Use Gemini to synthesize prompt with current brief
- Re-run full generation pipeline
- Store both original + operator-refined versions

#### 5. Gemini Prompt for Operator Refinement
**File**: `apps/backend/app/core/gemini_client.py` (new method) or inline in regenerate function

```python
async def refine_brief_with_operator_prompt(
    self,
    extraction_summary: str,
    current_brief_summary: str,
    brand_tokens_summary: str,
    operator_prompt: str,
) -> dict:
    """
    Use operator natural-language prompt to refine visual redesign brief.
    
    Constraints:
    - Do NOT rewrite extracted product facts
    - Do NOT invent testimonials or pricing
    - Do NOT change brand colors/tokens
    - Only refine: section order, component choices, visual tone, CTA strategy
    """
    
    prompt = f"""You are a design brief refinement assistant. An operator has provided refinement guidance on an existing website redesign. Your job is to synthesize their request with the current brief.

Current brief summary:
{current_brief_summary}

Brand tokens:
{brand_tokens_summary}

Original extraction:
{extraction_summary}

Operator refinement request:
"{operator_prompt}"

Produce a JSON object with refined guidance for visual redesign:
{{
  "refinedFocus": "Updated design direction",
  "sectionOrder": ["section1", "section2", ...],
  "componentSuggestions": [
    {{"section": "Hero", "suggestedComponent": "hero-split-editorial"}},
    ...
  ],
  "ctaStrategy": "Refined CTA approach",
  "visualTone": "Updated visual tone",
  "additionalNotes": "Implementation hints"
}}

CONSTRAINTS:
- Do NOT rewrite extracted product facts or content
- Do NOT invent testimonials, pricing, or claims not in source
- Do NOT change brand colors or visual tokens
- Do NOT suggest components that don't exist
- Keep changes grounded in the operator's guidance and extraction data

Only return valid JSON, no additional text.
"""
    
    response = await self.generate_text(prompt, temperature=0.6, max_tokens=1500)
    return self.extract_json_from_response(response)
```

#### 6. Validation & Safety Guardrails
**File**: `apps/backend/app/core/sites.py`

Add function:
```python
def validate_operator_prompt(prompt: str) -> tuple[bool, str]:
    """
    Validate operator prompt for safety.
    Returns (is_valid, error_message).
    """
    blocked_terms = [
        "testimonial",
        "fake",
        "invented",
        "pricing",
        "price",
        "cost",
        "guarantee",
        "promise",
        "10x",
        "guaranteed",
        "exclusive offer"
    ]
    
    lower = prompt.lower()
    for term in blocked_terms:
        if term in lower:
            return False, f"Prompts cannot include '{term}'. Keep changes grounded in extracted source data."
    
    if len(prompt) < 10:
        return False, "Prompt must be at least 10 characters"
    
    if len(prompt) > 500:
        return False, "Prompt must be less than 500 characters"
    
    return True, ""
```

#### 7. Job Dispatch (Celery/Background)
**File**: `apps/backend/app/core/tasks.py`

```python
@celery.task(bind=True, name="regenerate_site_with_prompt")
def regenerate_site_with_prompt_task(
    self,
    site_id: str,
    prompt_id: str,
    operator_id: str,
) -> dict:
    """Celery task wrapper for async regeneration."""
    job_id = self.request.id
    try:
        result = asyncio.run(
            sites_repository.regenerate_site_with_prompt(
                site_id=site_id,
                prompt_id=prompt_id,
                operator_id=operator_id,
                job_id=job_id,
            )
        )
        return result
    except Exception as e:
        # Update prompt: status="failed", reason=str(e)
        # Update job status
        raise
```

---

### Frontend Tasks (40% of work)

#### 1. Refinement Prompt Input Component
**File**: `apps/web/src/components/refinement-prompt-input.tsx` (NEW)

```typescript
export const RefinementPromptInput = ({
  siteId,
  onSubmit,
  isLoading,
}: {
  siteId: string;
  onSubmit: (prompt: string) => Promise<void>;
  isLoading: boolean;
}) => {
  const [prompt, setPrompt] = useState("");
  const [error, setError] = useState("");
  
  const handleSubmit = async () => {
    if (!prompt.trim()) {
      setError("Prompt cannot be empty");
      return;
    }
    if (prompt.length > 500) {
      setError("Prompt must be less than 500 characters");
      return;
    }
    try {
      await onSubmit(prompt);
      setPrompt("");
      setError("");
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="rounded-2xl border border-line bg-panel-2 p-6">
      <label className="block text-sm font-semibold text-text mb-2">
        Redesign Refinement Prompt
      </label>
      <textarea
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        placeholder='E.g., "Make this feel more premium and modern while keeping the core product story intact."'
        maxLength={500}
        disabled={isLoading}
        className="w-full rounded-lg border border-line bg-panel px-4 py-3 text-text placeholder-muted focus:outline-none focus:ring-2 focus:ring-accent resize-none"
        rows={4}
      />
      <div className="mt-2 flex items-center justify-between text-xs text-muted">
        <span>{prompt.length}/500</span>
        {error && <span className="text-rose-500">{error}</span>}
      </div>
      <button
        onClick={handleSubmit}
        disabled={isLoading || !prompt.trim()}
        className="mt-4 px-6 py-2.5 rounded-lg bg-accent text-white font-medium hover:opacity-90 disabled:opacity-50 transition-opacity"
      >
        {isLoading ? "Processing..." : "Submit Refinement"}
      </button>
    </div>
  );
};
```

#### 2. Prompt History Display
**File**: `apps/web/src/components/prompt-history.tsx` (NEW)

```typescript
export const PromptHistory = ({
  prompts,
  currentPromptId,
}: {
  prompts: RefinementPromptRecord[];
  currentPromptId?: string;
}) => {
  if (!prompts.length) return null;

  return (
    <div className="rounded-2xl border border-line bg-panel-2 p-6">
      <h3 className="text-sm font-semibold text-text mb-4">Refinement History</h3>
      <div className="space-y-3">
        {prompts.map((prompt) => (
          <div
            key={prompt.id}
            className={`rounded-lg border p-3 ${
              prompt.id === currentPromptId
                ? "border-accent bg-accent/10"
                : "border-line bg-panel"
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-text">
                {prompt.submittedAt && new Date(prompt.submittedAt).toLocaleDateString()}
              </span>
              <Badge
                className={
                  prompt.status === "success"
                    ? "border-green-500/40 bg-green-500/10 text-green-100"
                    : prompt.status === "failed"
                      ? "border-rose-500/40 bg-rose-500/10 text-rose-100"
                      : "border-blue-500/40 bg-blue-500/10 text-blue-100"
                }
              >
                {prompt.status}
              </Badge>
            </div>
            <p className="text-sm text-muted italic">"{prompt.promptText}"</p>
            {prompt.qualityScore !== undefined && (
              <div className="mt-2 text-xs text-text">
                Quality Score: {prompt.qualityScore}/100
              </div>
            )}
            {prompt.failureReason && (
              <div className="mt-2 text-xs text-rose-400">{prompt.failureReason}</div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
```

#### 3. Admin Workspace Integration
**File**: `apps/web/src/app/nsa/sites/[id]/page.tsx` (UPDATED)

Add new card after "Visual QA Analysis":
```typescript
// After existing Visual QA card...

{site ? (
  <Card>
    <CardHeader>
      <CardTitle>Operator Refinement</CardTitle>
      <CardDescription>Iteratively improve the preview with natural-language guidance</CardDescription>
    </CardHeader>
    <CardContent className="space-y-4">
      <RefinementPromptInput
        siteId={id}
        onSubmit={async (prompt) => {
          const res = await fetch(`/api/sites/${id}/regenerate`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ refinementPrompt: prompt }),
          });
          if (!res.ok) throw new Error(await res.text());
          const data = await res.json();
          // Trigger refresh/polling to show new version
          window.location.reload();
        }}
        isLoading={false}
      />
      
      <PromptHistory
        prompts={site.promptHistory || []}
        currentPromptId={site.refinementPromptId}
      />
    </CardContent>
  </Card>
) : null}
```

#### 4. API Client Functions
**File**: `apps/web/src/lib/api/sites.ts` (UPDATED)

Add functions:
```typescript
export async function submitRefinementPrompt(
  siteId: string,
  prompt: string,
): Promise<{ siteId: string; promptId: string; status: string }> {
  const res = await fetch(`/api/sites/${siteId}/regenerate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refinementPrompt: prompt }),
  });
  if (!res.ok) throw new Error(`Refinement failed: ${res.statusText}`);
  return res.json();
}

export async function getPromptHistory(siteId: string) {
  const res = await fetch(`/api/sites/${siteId}/prompts`);
  if (!res.ok) throw new Error("Failed to load prompt history");
  return res.json();
}
```

---

## Testing Requirements

### Backend Unit Tests (New)
**File**: `apps/backend/tests/test_refinement_prompt.py`

```python
class TestRefinementPrompt:
    def test_submit_refinement_prompt_success(self)
    def test_submit_refinement_prompt_blocked_terms(self)
    def test_submit_refinement_prompt_too_long(self)
    def test_refine_brief_with_gemini(self)
    def test_regenerate_with_prompt_quality_check(self)
    def test_regenerate_with_prompt_force_override(self)
    def test_prompt_history_persistence(self)
    def test_update_prompt_result_success(self)
    def test_update_prompt_result_failure(self)
    
# 9+ tests, all async with mocked Gemini/database
```

### Frontend Component Tests (New)
**File**: `apps/web/src/components/__tests__/refinement-prompt-input.test.tsx`

```typescript
describe("RefinementPromptInput", () => {
  test("renders textarea and submit button")
  test("disables submit when empty")
  test("validates max length (500 chars)")
  test("calls onSubmit with prompt text")
  test("shows error on submission failure")
  test("clears prompt after successful submit")
})

describe("PromptHistory", () => {
  test("renders prompt history list")
  test("shows current prompt with highlight")
  test("displays status badge (success/failed/pending)")
  test("shows quality score if available")
  test("shows failure reason if present")
})
```

### Integration Test (New)
**File**: `apps/backend/tests/test_regeneration_workflow.py`

```python
class TestRegenerationWorkflow:
    async def test_full_regeneration_workflow(self):
        """
        End-to-end: submit prompt → regenerate → QA → update site.
        """
        # 1. Load existing site
        # 2. Submit prompt via endpoint
        # 3. Wait for job completion
        # 4. Verify new version created
        # 5. Verify prompt_history updated
        # 6. Verify screenshot captured and QA'd
        # 7. Verify public preview updated (if quality >= 75)
```

---

## Implementation Checklist

### Backend (Days 1-2)
- [ ] Add `RefinementPromptRecord` and history fields to schemas
- [ ] Implement `submit_refinement_prompt()` in SiteRepository
- [ ] Implement `update_prompt_result()` in SiteRepository
- [ ] Add `validate_operator_prompt()` safety checks
- [ ] Create `regenerate_site_with_prompt()` async function
- [ ] Add Gemini `refine_brief_with_operator_prompt()` method
- [ ] Implement `POST /api/sites/{id}/regenerate` endpoint
- [ ] Add Celery task for background processing
- [ ] Write 9+ unit tests for prompt handling
- [ ] Write integration test for full workflow
- [ ] Run all tests (target: 27+ tests passing)

### Frontend (Days 1-2)
- [ ] Create `RefinementPromptInput` component
- [ ] Create `PromptHistory` component
- [ ] Add components to admin workspace
- [ ] Add API client functions
- [ ] Add component unit tests (8+ tests)
- [ ] Add error handling and user feedback
- [ ] Test submit → progress → completion flow
- [ ] Verify prompt history display

### Documentation (Day 2)
- [ ] Document Gemini refinement prompt
- [ ] Document regeneration workflow diagram
- [ ] Document safety guardrails
- [ ] Document operator best practices
- [ ] Update API documentation
- [ ] Create Phase 16 completion summary

---

## Key Constraints

1. **Safety**: Operator prompts cannot rewrite extracted facts, invent content, or make unsupported claims
2. **Quality**: Regenerated previews must pass same QA as initial generation (quality >= 75 to publish)
3. **Traceability**: Every prompt and resulting version linked in immutable history
4. **Repeatability**: Same prompt + same site state = deterministic output (with minor variance from Gemini)
5. **Backward Compatibility**: Existing generation flow unchanged; prompts are optional

---

## Success Criteria

- ✅ Operators can submit natural-language refinement prompts
- ✅ Backend validates and processes prompts safely
- ✅ Regeneration preserves brand integrity and extracted content
- ✅ Screenshot QA blocks low-quality reruns
- ✅ Prompt history visible in admin with outcome tracking
- ✅ Public preview updates only after QA success
- ✅ All tests passing (27+ tests)
- ✅ Full end-to-end workflow tested and documented

---

## Gemini Prompts Summary

### Refinement Synthesis Prompt
**Purpose**: Synthesize operator prompt with current brief to refine component choices and visual tone
**Temperature**: 0.6 (balanced creativity + determinism)
**Max Tokens**: 1500
**Model**: gemini-2.0-flash

```
You are a design brief refinement assistant. An operator has provided refinement guidance on an existing website redesign. Synthesize their request with the current brief while preserving extracted content and brand tokens.

[Full prompt in section "5. Gemini Prompt for Operator Refinement" above]
```

---

## Deployment Notes

- **Environment Variables**: No new required variables (uses existing Gemini config)
- **Database Migration**: Add `refinementPromptId`, `promptHistory` fields to GeneratedSite/GeneratedSiteVersion
- **API Changes**: New `POST /api/sites/{id}/regenerate` endpoint
- **Background Jobs**: New Celery task `regenerate_site_with_prompt`
- **Performance**: Regeneration adds 10-20s to generation job (same as Phase 15 QA)

---

## Files to Create/Modify

### Backend
- `apps/backend/app/schemas/site.py` → Add RefinementPromptRecord
- `apps/backend/app/core/sites.py` → Add regeneration methods + validation
- `apps/backend/app/api/sites.py` → Add /regenerate endpoint
- `apps/backend/app/core/tasks.py` → Add Celery task
- `apps/backend/tests/test_refinement_prompt.py` → NEW (9+ tests)
- `apps/backend/tests/test_regeneration_workflow.py` → NEW (integration test)

### Frontend
- `apps/web/src/components/refinement-prompt-input.tsx` → NEW
- `apps/web/src/components/prompt-history.tsx` → NEW
- `apps/web/src/app/nsa/sites/[id]/page.tsx` → UPDATED (add prompt UI)
- `apps/web/src/lib/api/sites.ts` → UPDATED (add submit function)
- `apps/web/src/components/__tests__/refinement-prompt-input.test.tsx` → NEW (8+ tests)
- `apps/web/src/components/__tests__/prompt-history.test.tsx` → NEW

### Documentation
- `docs/PHASE-16-IMPLEMENTATION-SUMMARY.md` → NEW (technical guide)
- `docs/PHASE-16-DELIVERABLES.md` → NEW (checklist)
- Update `docs/phase-16-implementation-prompt.md` → Status: Complete ✅

---

## References

- Phase 15 Code: screenshot_analyzer.py, premium-sections.tsx
- Existing regenerate logic: sites.py `republish_site()`, `run_generation_job()`
- Gemini integration: gemini_client.py methods
- Database models: schemas/site.py
- Admin workspace: nsa/sites/[id]/page.tsx

---

## Ready for Implementation ✅

This prompt provides complete, detailed guidance for Phase 16 implementation. All dependencies from Phase 15 are complete and verified. The implementation is straightforward, testable, and follows established patterns in the codebase.

**Estimated Time**: 2-3 days for full implementation + testing + documentation
