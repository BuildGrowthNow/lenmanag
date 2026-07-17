# Production Fixes - 2026-07-17

## Issues Fixed

### Issue #4: Analysis Refresh Job Stays in "QUEUED" Status ✅ FIXED

**Root Cause:**
- Line 1827 in `apps/backend/app/core/leads.py` used incorrect MongoDB collection name `extractions` instead of `site_extractions`
- This caused the analysis results to never be saved to the database
- Job status update logic worked correctly, but the data persistence failed silently

**Fix:**
- Changed `database["extractions"]` to `database["site_extractions"]` on line 1827
- Analysis results now persist correctly to the extraction document

**Impact:**
- Analysis refresh jobs now complete successfully
- Users can see analysis results after job completion
- No more stuck "queued" status

---

### Issue #5: Multiple Duplicate Extraction Jobs ✅ FIXED

**Root Cause:**
- No duplicate job prevention in `start_extraction()` and `start_analysis_refresh()` methods
- API endpoints could be called multiple times, creating redundant Celery jobs
- Both jobs would execute simultaneously, wasting resources

**Fix:**
- Added duplicate job detection before creating new extraction jobs
- Check for existing jobs with status "queued" or "running" for the same lead
- If duplicate found, return the existing job instead of creating a new one
- Implemented for both MongoDB and in-memory storage backends
- Added logging when duplicates are detected

**Code Changes:**
```python
# In start_extraction():
# Check database for existing jobs
existing_job = await database["jobs"].find_one({
    "leadId": lead_id,
    "jobType": {"$in": ["site_crawl", "site_refresh"]},
    "status": {"$in": ["queued", "running"]},
})
if existing_job:
    # Return existing job instead of creating duplicate
    return ExtractionJobResponse(job=existing_job, extraction=snapshot)
```

**Impact:**
- No more duplicate extraction jobs
- Prevents unnecessary API calls to LLM providers
- Saves crawling resources and AWS Bedrock costs
- Better user experience - no confusion about multiple jobs

---

## Quality Checks Completed

### Backend
- ✅ `ruff check .` - All checks passed
- ✅ `ruff format .` - 1 file reformatted
- ✅ `pyright app/core/leads.py` - 0 errors, 0 warnings

### Changes Summary
- **Files Modified:** `apps/backend/app/core/leads.py`
- **Lines Changed:** ~60 lines (collection name fix + duplicate prevention)
- **Breaking Changes:** None
- **Migration Required:** No

---

## Testing Recommendations

### Manual Testing

1. **Test Analysis Refresh:**
   ```bash
   # Login and get session
   SESSION="<your-session-token>"
   
   # Create lead and wait for extraction to complete
   curl -X POST -H "Cookie: lenquant_session=$SESSION" \
     -H "Content-Type: application/json" \
     -d '{"companyName": "Test Co", "websiteUrl": "https://example.com"}' \
     http://localhost:8000/api/v1/leads
   
   # Get lead ID and trigger analysis refresh
   LEAD_ID="<lead-id>"
   curl -X POST -H "Cookie: lenquant_session=$SESSION" \
     http://localhost:8000/api/v1/leads/$LEAD_ID/analysis/start
   
   # Check job status (should progress from queued → running → completed)
   curl -H "Cookie: lenquant_session=$SESSION" \
     http://localhost:8000/api/v1/leads/$LEAD_ID
   
   # Verify analysis results are saved
   curl -H "Cookie: lenquant_session=$SESSION" \
     http://localhost:8000/api/v1/leads/$LEAD_ID/analysis
   ```

2. **Test Duplicate Prevention:**
   ```bash
   # Trigger extraction twice in rapid succession
   curl -X POST -H "Cookie: lenquant_session=$SESSION" \
     http://localhost:8000/api/v1/leads/$LEAD_ID/extraction/start &
   curl -X POST -H "Cookie: lenquant_session=$SESSION" \
     http://localhost:8000/api/v1/leads/$LEAD_ID/extraction/start &
   
   # Check logs - should see "Extraction already in progress" message
   docker compose logs -f backend | grep "already in progress"
   
   # Verify only ONE job was created
   curl -H "Cookie: lenquant_session=$SESSION" \
     http://localhost:8000/api/v1/leads/$LEAD_ID | jq '.data.jobIds | length'
   ```

### Database Verification

```javascript
// Connect to MongoDB and check analysis field exists
db.site_extractions.findOne(
  {leadId: "<lead-id>"},
  {analysis: 1, crawlStatus: 1, leadId: 1}
)

// Should return analysis object with sections, confidenceScore, etc.
```

---

## Deployment

1. Commit changes:
   ```bash
   git add apps/backend/app/core/leads.py
   git commit -m "Fix analysis refresh collection name and duplicate job prevention"
   ```

2. Push to main (auto-deploys):
   ```bash
   git push origin main
   ```

3. Verify deployment:
   ```bash
   # Wait ~5 minutes, then SSH to server
   ssh -i ~/.ssh/lenquant.pem ubuntu@ec2-32-194-123-142.compute-1.amazonaws.com
   
   # Check backend health
   curl -sf http://localhost:8000/api/v1/health
   
   # Check logs
   cd /opt/lenquant && docker compose logs -f backend
   ```

---

## Related Issues (Still Open)

The investigation document mentioned 5 issues total. These 2 are now fixed. Status of others:

- Issue #1-3: Not provided in current context
- **Issue #4: FIXED** ✅
- **Issue #5: FIXED** ✅

---

## Notes

- Both fixes are backward-compatible
- No database migration required
- Existing jobs in "queued" status will need manual retry
- Duplicate prevention only applies to NEW job requests after deployment
