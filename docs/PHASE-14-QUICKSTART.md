# Phase 14 Quick Start Guide

## What You're Building

A system that transforms crawled websites into **premium, Awwwards-worthy redesigns** using AI-driven design decisions and premium React components.

**Key insight:** Gemini analyzes sections and recommends components. The frontend renders those components beautifully. Vision LLM validates quality. Repeat until premium.

---

## The 4 Phases at a Glance

| Phase | What | Duration | Key Files |
|-------|------|----------|-----------|
| **14.1** | Gemini integration + visual redesign analysis | 3-4 days | `gemini_client.py`, `visual_redesign.py` |
| **14.2** | Premium React components + renderer update | 4-5 days | `premium/*.tsx`, `component-registry.ts` |
| **14.3** | Screenshot analysis + quality iteration | 3-4 days | `screenshot_analyzer.py` |
| **14.4** | Public deployment + client handoff | 2-3 days | `public_deployment.py` |

---

## Start Here: Phase 14.1

### 1. Get Gemini API Key

```bash
# Go to https://ai.google.dev/
# Create API key
# Add to .env:
GEMINI_API_KEY=your-key-here
```

### 2. Create Gemini Client

Follow `phase-14-1-implementation-guide.md`:
- Create `apps/backend/app/core/gemini_client.py`
- Create `apps/backend/app/core/visual_redesign.py`
- Update `apps/backend/app/core/config.py`

### 3. Integrate into Generation Job

In `apps/backend/app/core/sites.py`, after `_section_stack()`:
```python
from app.core.visual_redesign import generate_visual_redesign_brief

visual_redesign_briefs = await generate_visual_redesign_brief(
    brief=brief,
    extraction=extraction,
    client_brand=brand_tokens,
)
brief.visualRedesign = visual_redesign_briefs
```

### 4. Test

```bash
cd apps/backend
pytest tests/test_visual_redesign.py -v
```

---

## Then: Phase 14.2

### 1. Create Components

Follow `phase-14-2-implementation-guide.md`:
- Create `apps/web/src/components/premium/` directory
- Create all 10 components (copy-paste from guide)
- Create `apps/web/src/lib/component-registry.ts`

### 2. Update Renderer

In `apps/web/src/app/sites/[slug]/page.tsx`:
```typescript
import { getComponent, isValidComponentId } from '@/lib/component-registry';

function renderSection(section: SiteSection, ...) {
  // NEW: Check componentId first
  if (section.componentId && isValidComponentId(section.componentId)) {
    const Component = getComponent(section.componentId);
    if (Component) {
      return <Component section={section} brandTokens={...} paletteMode={...} dna={...} />;
    }
  }
  
  // FALLBACK: Existing regex-based rendering
  // ... rest of code
}
```

### 3. Test

```bash
cd apps/web
npm test
```

---

## Then: Phase 14.3 & 14.4

Follow the implementation guides for:
- `phase-14-3-implementation-guide.md` (Screenshot analysis)
- `phase-14-4-implementation-guide.md` (Public deployment)

---

## Key Files to Know

### Backend
```
apps/backend/app/core/
├── gemini_client.py          (Gemini API wrapper)
├── visual_redesign.py        (Analysis service)
├── screenshot_analyzer.py    (Quality evaluation)
├── public_deployment.py      (Deployment service)
└── sites.py                  (Integration point)
```

### Frontend
```
apps/web/src/
├── components/premium/       (10 premium components)
├── lib/component-registry.ts (Component mapping)
└── app/sites/[slug]/page.tsx (Enhanced renderer)
```

### Configuration
```
.env
├── GEMINI_API_KEY
├── VISUAL_REDESIGN_ENABLED
├── SCREENSHOT_ANALYSIS_ENABLED
└── DEPLOYMENT_PROVIDER
```

---

## Environment Variables (Copy-Paste)

```bash
# Gemini Configuration
GEMINI_API_KEY=your-api-key-here
GEMINI_MODEL=gemini-2.0-flash
GEMINI_VISION_MODEL=gemini-2.0-flash

# Visual Redesign
VISUAL_REDESIGN_ENABLED=true
VISUAL_REDESIGN_MAX_ITERATIONS=3
VISUAL_REDESIGN_QUALITY_THRESHOLD=75

# Screenshot Analysis
SCREENSHOT_ANALYSIS_ENABLED=true
SCREENSHOT_TIMEOUT_SECONDS=30

# Public Deployment
DEPLOYMENT_PROVIDER=vercel
VERCEL_TOKEN=your-token
PUBLIC_DOMAIN=redesigns.example.com
```

---

## Testing Checklist

### Phase 14.1
- [ ] Gemini API key works
- [ ] `gemini_client.py` tests pass
- [ ] Visual redesign briefs are generated
- [ ] No errors in generation job

### Phase 14.2
- [ ] All 10 components render
- [ ] Component registry works
- [ ] Renderer checks componentId first
- [ ] Responsive on mobile/tablet/desktop
- [ ] No console errors

### Phase 14.3
- [ ] Screenshots capture correctly
- [ ] Vision LLM evaluates quality
- [ ] Iteration loop works
- [ ] Final designs are premium

### Phase 14.4
- [ ] Sites deploy to CDN
- [ ] Public URLs are shareable
- [ ] Analytics tracking works

---

## Common Issues & Fixes

### Gemini API Key Error
```
Error: GEMINI_API_KEY not configured
Fix: Add GEMINI_API_KEY to .env
```

### JSON Parsing Error
```
Error: Invalid JSON in Gemini response
Fix: Check prompt formatting, increase max_tokens
```

### Component Not Found
```
Error: Component 'services-grid' not found
Fix: Check component-registry.ts has all 10 components
```

### Screenshot Capture Fails
```
Error: Playwright timeout
Fix: Increase SCREENSHOT_TIMEOUT_SECONDS
```

---

## Performance Targets

- **Time per site:** 5-10 minutes
- **Cost per site:** $0.15-0.30
- **Design quality:** ≥80/100
- **Success rate:** ≥90%

---

## Documentation Map

```
PHASE-14-SUMMARY.md                    ← Start here for overview
├── phase-14-visual-redesign-workflow.md  (Full architecture)
├── phase-14-1-implementation-guide.md    (Gemini integration)
├── phase-14-2-implementation-guide.md    (Premium components)
├── phase-14-3-implementation-guide.md    (Screenshot analysis) [TBD]
├── phase-14-4-implementation-guide.md    (Public deployment) [TBD]
└── PHASE-14-QUICKSTART.md               (This file)
```

---

## Next Steps

1. **Read** `PHASE-14-SUMMARY.md` for full overview
2. **Follow** `phase-14-1-implementation-guide.md` to start
3. **Test** with real extraction data
4. **Iterate** through phases 14.2, 14.3, 14.4
5. **Deploy** to production

---

## Success Looks Like

✅ User provides website URL  
✅ System crawls and extracts content  
✅ Gemini analyzes sections  
✅ Frontend renders with premium components  
✅ Vision LLM validates quality  
✅ Site is deployed publicly  
✅ Client receives shareable link  
✅ Client sees beautiful, unique redesign  

---

## Questions?

1. Check the phase-specific implementation guides
2. Review the main architecture document
3. Check environment variables
4. Review test cases for examples
5. Check logs for error messages

---

**Ready to build?** Start with Phase 14.1 → `phase-14-1-implementation-guide.md`

