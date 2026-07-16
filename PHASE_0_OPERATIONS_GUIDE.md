# Phase 0: Pipeline Fix - Operations & Troubleshooting Guide

## Quick Reference

**What Changed**: Auto pipeline now uses master brief (AI-powered) instead of old brief (keyword-based)
**Status**: ✅ Production Deployed
**Commit**: 3caa728
**Impact**: Better brief quality, no operator intervention needed

---

## For Operations Team

### What Users Will Notice

**Before (Broken)**:
```
Auto-generated site briefs had:
- Tone: "Primary logo, Secondary logo" ❌
- Services: "Services, About, Contact" ❌
- Audience: (empty) ❌
- Quality: Shallow, generic ❌
```

**After (Fixed)**:
```
Auto-generated site briefs now have:
- Tone: "Professional with friendly undertones emphasizing trust" ✅
- Services: "24/7 Emergency HVAC Repair, Installation, Maintenance" ✅
- Audience: "Homeowners in suburbs, ages 35-55, middle-income" ✅
- Quality: Rich, specific, business-tailored ✅
```

### Auto Mode Pipeline (Now Correct)

When a lead is created with `pipelineMode: "auto"`:

```
1. EXTRACTION (operator/user action)
   └─→ Website crawl starts
   └─→ Status: "extracting" → "extracted"

2. MASTER BRIEF (automatic)
   └─→ AI analyzes extraction
   └─→ Generates strategy brief
   └─→ Auto-approves
   └─→ Status: "briefing" → "brief_ready"

3. SITE GENERATION (automatic)
   └─→ Compiler builds HTML
   └─→ Status: "generating" → "qa" → "ready"
```

**No operator approval needed** - everything runs sequentially.

### Manual Mode Pipeline (Unchanged)

When a lead is created with `pipelineMode: "manual"`:

```
1. EXTRACTION (operator action)
   └─→ Status: "extracted" → pause

2. OPERATOR REVIEWS EXTRACTION
   └─→ Operator approves extraction

3. MASTER BRIEF (automatic or operator-triggered)
   └─→ Operator clicks "Generate Brief"
   └─→ AI generates strategy
   └─→ Status: "brief_ready" → pause

4. OPERATOR REVIEWS BRIEF
   └─→ Operator clicks "Approve & Generate"
   └─→ Status: "generating" → "ready"
```

---

## Monitoring & Logs

### Key Log Entries (Search for These)

```
✅ EXPECTED (Correct Flow):
"Master brief generated" - AI generated strategy brief
"Master brief approved" - Auto-approved in pipeline
"Site generation started" - Beginning site compilation

❌ UNEXPECTED (Problem):
"create_brief" - Old brief system being used (bug)
"Brief generation failed" - Master brief generation error
"brief_requires_extraction" - Missing extraction data
```

### Checking Pipeline Status

```bash
# Check lead status
curl -s -H "Cookie: lenquant_session=$SESSION" \
  "http://localhost:8000/api/v1/leads/$LEAD_ID" | jq .data.lead.pipelineStage

# Expected sequence:
# "new" → "extracting" → "extracted" → "briefing" → "brief_ready" → "generating" → "qa" → "ready"

# Check master brief
curl -s -H "Cookie: lenquant_session=$SESSION" \
  "http://localhost:8000/api/v1/leads/$LEAD_ID/master-brief" | jq .data.approvalState
# Expected: "approved" (for auto mode) or "pending" (for manual mode)
```

### Common Issues

#### Issue 1: Brief Generation Takes Too Long

**Symptom**: Status stuck at "briefing" for > 2 minutes

**Cause**: LLM API latency (Claude model is slow)

**Solution**:
1. Check logs: `docker compose logs -f backend | grep "master brief"`
2. Wait up to 3 minutes (normal range for LLM analysis)
3. If > 5 minutes, restart backend: `docker compose restart backend`

#### Issue 2: "Brief generation returned no result"

**Symptom**: Status shows "needs_attention", detail says "Master brief generation returned no result"

**Cause**: Extraction missing required data

**Solution**:
1. Check extraction quality: `curl -s -H "Cookie: ..." "http://localhost:8000/api/v1/leads/$LEAD_ID/extraction" | jq .data.summary`
2. Verify website is reachable and has content
3. Try manual extraction refresh: `POST /leads/{id}/extraction/refresh`
4. If fails, check website URL is valid

#### Issue 3: "Brief not approved"

**Symptom**: Site generation fails with "brief_not_approved"

**Cause**: Auto approval didn't complete

**Solution**:
1. Manually approve: `POST /leads/{id}/master-brief/approve` with body `{"approvedBy": "auto"}`
2. Then trigger generation: `POST /sites/{id}/generate`

#### Issue 4: Old brief system being used

**Symptom**: Master brief looks fine, but site generation uses old brief

**Cause**: Site generation fell back to legacy brief

**Solution**:
1. Check both briefs exist:
   - `GET /leads/{id}/brief` (legacy)
   - `GET /leads/{id}/master-brief` (new)
2. Both should be "approved"
3. Site generation prefers master brief - if both exist, master is used

---

## Database Queries

### MongoDB - Check Brief Status

```javascript
// Check a specific lead's briefs
db.master_briefs.findOne(
  {leadId: "LEAD_ID"},
  {sort: {version: -1}}
)

// Check all briefs created today
db.master_briefs.find({
  createdAt: {
    $gte: new Date(new Date().toISOString().split('T')[0])
  }
}).count()

// Check approval states
db.master_briefs.aggregate([
  {$group: {
    _id: "$approvalState",
    count: {$sum: 1}
  }}
])

// Check old briefs still exist (for backwards compat)
db.site_briefs.findOne(
  {leadId: "LEAD_ID"},
  {sort: {version: -1}}
)
```

---

## Testing Checklist

### Before Declaring Success

- [ ] Create lead in auto mode with `pipelineMode: "auto"`
- [ ] Extraction completes (wait ~30 seconds)
- [ ] Master brief auto-generated (check logs for "Master brief generated")
- [ ] Master brief auto-approved (check logs for "Master brief approved")
- [ ] Site generation starts (check logs for "Site generation started")
- [ ] Final site has good quality (check preview for business-relevant content)
- [ ] Brief fields are populated:
  - [ ] `businessGoal` - not generic
  - [ ] `primaryAudience` - specific demographics
  - [ ] `toneAndVoice` - sounds like the business
  - [ ] `sections` - real content, not bare headings
- [ ] Compare with manual mode - results should be similar

### Regression Tests

- [ ] Manual mode still works (operator approvals work)
- [ ] Legacy brief routes still work (backwards compatibility)
- [ ] Site generation works with both master and legacy briefs
- [ ] No increase in error rates
- [ ] No increase in brief generation latency

---

## Rollback Procedure

If critical issues found:

### Option 1: Fast Rollback (5 mins)

```bash
git revert 3caa728
git push
# Wait for GitHub Actions to deploy
```

### Option 2: Manual Rollback (2 mins)

SSH to production and edit:
```bash
vi /opt/lenquant/apps/backend/app/core/leads.py
# Change lines 667-687 back to using create_brief()
# Save and docker compose restart backend
```

### Verify Rollback

```bash
curl -s "http://localhost:8000/api/v1/health" | jq .
# Should return healthy status
```

---

## Deployment Verification

### Post-Deployment Checklist

- [ ] GitHub Actions deployed successfully
- [ ] SSH to EC2 and verify containers running: `docker compose ps`
- [ ] Check backend health: `curl -sf http://localhost:8000/api/v1/health`
- [ ] Check logs for errors: `docker compose logs backend | grep -i error | head -10`
- [ ] Test auto pipeline with new lead
- [ ] Verify master brief created (not old brief)
- [ ] Check site generation completed successfully

### Metrics to Monitor (24 Hours)

- Brief generation success rate (should be > 95%)
- Average brief generation time (expect 5-15 seconds)
- Site generation success rate (should stay > 90%)
- Error rate on brief-related endpoints (should be < 1%)

---

## Performance Impact

### Expected Metrics

- **Brief generation latency**: +2-5 seconds (LLM call)
- **Site generation latency**: No change
- **Database disk usage**: No significant change
- **API request volume**: No change (same endpoints)

### Cost Impact

- **LLM cost per brief**: ~$0.02-0.05 (Claude analysis)
- **Total cost per lead**: ~$0.05-0.10 (extraction + analysis + brief)
- **ROI**: Better quality = fewer regenerations = saves cost

---

## Support & Escalation

### If Something Goes Wrong

**Tier 1 - Check Logs**:
```bash
docker compose logs -f backend | grep -E "master brief|error"
```

**Tier 2 - Check Database**:
```bash
db.master_briefs.findOne({leadId: "LEAD_ID"})
# Verify doc structure and approval state
```

**Tier 3 - Manual Intervention**:
```bash
# Manually approve a brief
curl -X POST "http://localhost:8000/api/v1/leads/{id}/master-brief/approve" \
  -H "Cookie: lenquant_session=$SESSION" \
  -H "Content-Type: application/json" \
  -d '{"approvedBy": "auto", "notes": "Manual approval"}'

# Trigger generation manually
curl -X POST "http://localhost:8000/api/v1/sites/{id}/generate" \
  -H "Cookie: lenquant_session=$SESSION"
```

**Tier 4 - Escalate**:
- Contact engineering team
- Provide: Lead ID, timestamp, logs from `docker compose logs backend`
- Consider rollback to previous version

---

## Next Steps

Phase 0 is complete. When ready for Phase 1:

**Phase 1**: Add LLM analysis layer (2-3 hours)
- Replace keyword detection with Claude analysis
- Analyze services, tone, audience, CTAs
- Works in any language
- Better accuracy, no garbage data

See `EXTRACTION_REFACTOR_PLAN.md` for full implementation plan.

---

**Operations Guide - Phase 0: Pipeline Fix**

Last Updated: 2026-07-16
Status: Production Deployed ✅
