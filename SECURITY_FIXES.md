# Security and Reliability Fixes

This document outlines the security and reliability improvements implemented to address the identified issues.

## 1. ✅ Rate Limiting on Auth Endpoints

**Issue**: `/auth/verify` and `/auth/login` endpoints were vulnerable to brute-force attacks with no throttling or rate limiting.

**Fix**:
- Created `app/core/rate_limiter.py` with in-memory rate limiter using sliding window algorithm
- Applied to auth endpoints with strict limits: 5 attempts per 15 minutes per IP
- Includes IP extraction from X-Forwarded-For headers for proxy/load balancer support
- Returns 429 status with Retry-After header when limit exceeded

**Files Modified**:
- `apps/backend/app/core/rate_limiter.py` (NEW)
- `apps/backend/app/api/auth.py`

**Future Improvements**: For production at scale, migrate to Redis-backed rate limiting using `slowapi` or `fastapi-limiter`.

---

## 2. ✅ Optimistic Locking for Concurrent Modifications

**Issue**: MongoDB operations didn't use transactions, allowing race conditions when multiple users modify the same lead/site simultaneously.

**Fix**:
- Implemented version-based optimistic locking in `update_lead()` method
- MongoDB replace operation now includes version check in query
- Returns error if version mismatch detected
- Automatically increments version on each update

**Files Modified**:
- `apps/backend/app/core/leads.py` - `update_lead()` method

**How it works**: 
```python
# Check version matches before update
result = await database["leads"].replace_one(
    {"id": lead_id, "version": current_version},
    updated_doc
)
if result.matched_count == 0:
    raise ValueError("Concurrent modification detected")
```

---

## 3. ✅ Comprehensive Input Validation for CSV Imports

**Issue**: CSV import had minimal validation, vulnerable to:
- Malformed files causing parsing errors
- Extremely large files causing OOM
- CSV injection attacks
- Encoding issues

**Fix**:
- File size limit: 10MB maximum
- Row count limit: 1000 rows maximum
- Encoding detection and safe decoding (UTF-8, fallback to Latin-1)
- CSV injection protection: reject files starting with `=`, `+`, `-`, `@`
- Proper CSV error handling with detailed error messages

**Files Modified**:
- `apps/backend/app/core/leads.py` - `import_csv()` method

**Validation Steps**:
1. Check file size < 10MB
2. Validate encoding (UTF-8 or Latin-1)
3. Detect suspicious CSV injection patterns
4. Parse with error handling
5. Limit rows to 1000

---

## 4. ✅ Pagination Limits and Validation

**Issue**: `offset` and `limit` parameters accepted arbitrary values, allowing:
- OOM attacks with `limit=1000000`
- Excessive database queries
- Denial of service

**Fix**:
- Maximum limit: 100 items per page
- Maximum offset: 10,000
- Validation in `list_leads()` with clear error messages
- Returns 400 Bad Request if limits exceeded

**Files Modified**:
- `apps/backend/app/core/leads.py` - `list_leads()` method
- `apps/backend/app/api/leads.py` - error handling

**Limits**:
```python
max_limit = 100    # Max items per page
max_offset = 10000 # Max skip count
```

---

## 5. ✅ Retry Policy and Failure Tracking for Extraction Jobs

**Issue**: Celery tasks caught all exceptions but only logged them. Failed jobs:
- Had no retry mechanism
- No dead-letter queue
- No UI notifications
- Failed silently

**Fix**:
- Configured automatic retry with exponential backoff and jitter
- Extraction jobs: 3 retries, max 10min backoff
- Site generation jobs: 2 retries, max 15min backoff
- Job status updated on each retry with failure context
- Detailed logging with retry count

**Files Modified**:
- `apps/backend/app/core/tasks.py` - both task functions

**Retry Configuration**:
```python
@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,  # 10 minutes
    retry_jitter=True,
    max_retries=3,
)
```

---

## 6. ✅ Automatic Refresh Mechanism for Frontend State

**Issue**: Frontend had no mechanism to detect extraction job completions. Users couldn't see updates without manual refresh.

**Fix**:
- Created `pollLeadUpdates()` function in frontend API
- Configurable polling interval (default 5 seconds)
- Clean abort mechanism
- Error handling for failed polls

**Files Modified**:
- `apps/web/src/lib/api/leads.ts`

**Usage Example**:
```typescript
const cleanup = pollLeadUpdates(
  { limit: 25 },
  (results) => setLeads(results.items),
  5000 // 5 second interval
);
// Later: cleanup() to stop polling
```

---

## 7. ✅ Path Validation for Asset Storage

**Issue**: S3 and GCS storage modules constructed paths without validation, potentially allowing:
- Path traversal attacks (`../../../etc/passwd`)
- Access to files outside intended buckets
- Overwriting system files

**Fix**:
- Created `_validate_path_component()` method in both storage backends
- Blocks: `..`, `.`, `/`, `\`, null bytes
- Only allows alphanumeric + hyphens/underscores
- Applied to all path construction operations

**Files Modified**:
- `apps/backend/app/core/asset_storage_s3.py`
- `apps/backend/app/core/asset_storage_gcs.py`

**Validation**:
```python
forbidden = ["..", ".", "/", "\\", "\x00"]
if any(f in component for f in forbidden):
    raise ValueError("Invalid path")
```

---

## 8. ✅ MongoDB Connection Pool Limits

**Issue**: Async Motor client could open unlimited connections, potentially:
- Exhausting MongoDB server connections
- Causing OOM on client side
- Degrading performance under load

**Fix**:
- Configured `maxPoolSize=50` (max connections)
- Configured `minPoolSize=10` (warm pool)
- Set timeouts for connection acquisition and socket operations
- Added idle connection cleanup (45s)

**Files Modified**:
- `apps/backend/app/core/mongo.py`

**Connection Pool Settings**:
```python
AsyncIOMotorClient(
    uri,
    maxPoolSize=50,
    minPoolSize=10,
    maxIdleTimeMS=45000,
    waitQueueTimeoutMS=10000,
    serverSelectionTimeoutMS=5000,
)
```

---

## Summary of Improvements

| Issue | Severity | Status | Prevention |
|-------|----------|--------|------------|
| No auth rate limiting | High | ✅ Fixed | Brute-force attacks prevented |
| Race conditions | Medium | ✅ Fixed | Optimistic locking added |
| CSV validation gaps | Medium | ✅ Fixed | Size, injection, encoding checks |
| Pagination attacks | Medium | ✅ Fixed | Hard limits enforced |
| Silent job failures | Medium | ✅ Fixed | Retry policy + logging |
| No frontend sync | Low | ✅ Fixed | Polling mechanism added |
| Path traversal risk | High | ✅ Fixed | Path validation added |
| Unlimited connections | Medium | ✅ Fixed | Pool limits configured |

---

## Testing Recommendations

1. **Rate Limiting**: Test with multiple rapid requests to verify 429 responses
2. **Optimistic Locking**: Simulate concurrent updates to same lead
3. **CSV Validation**: Try uploading malformed, large, and injection-attempt files
4. **Pagination**: Test with limit=10000 and offset=999999
5. **Job Retry**: Simulate extraction failures and verify retry behavior
6. **Frontend Polling**: Monitor network tab for polling requests
7. **Path Validation**: Try lead_id with `../` patterns
8. **Connection Pool**: Load test with concurrent requests

---

## Production Deployment Notes

1. **Rate Limiting**: Consider Redis-backed rate limiting for multi-instance deployments
2. **Monitoring**: Add metrics for:
   - Rate limit hits per endpoint
   - Concurrent modification conflicts
   - Job retry counts
   - Connection pool utilization
3. **Alerting**: Set up alerts for:
   - High rate limit rejection rate
   - Repeated job failures
   - Connection pool exhaustion
   - Path validation errors

---

## Maintenance

- Review rate limits quarterly and adjust based on usage patterns
- Monitor job failure rates and adjust retry configuration
- Periodically audit CSV import patterns for new attack vectors
- Keep connection pool settings tuned to database capacity
