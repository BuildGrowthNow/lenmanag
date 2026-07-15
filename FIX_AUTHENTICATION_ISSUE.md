# Authentication Issue Fix

## Problem
When logging in with `fern2gue@gmail.com`, the login succeeds but accessing the dashboard fails with a Server Components render error. The backend logs show:

```
INFO: POST /api/v1/auth/login HTTP/1.1" 200 OK
INFO: GET /api/v1/analytics/dashboard HTTP/1.1" 401 Unauthorized
```

## Root Cause
**Cross-domain cookie issue**: The session cookie is set by the backend at `sites-api.lenquant.com` but the frontend runs on `sites.lenquant.com`. When Next.js Server Components try to fetch data during server-side rendering, the cookie isn't available because:

1. Login happens **client-side** (browser) - cookie gets set for `sites-api.lenquant.com`
2. Dashboard renders **server-side** (Next.js SSR) - tries to fetch from backend but cookies aren't shared across domains
3. `SESSION_COOKIE_DOMAIN` is empty, so cookie is tied to the exact domain that set it

## Solution
Set `SESSION_COOKIE_DOMAIN=.lenquant.com` to share cookies across all `*.lenquant.com` subdomains.

## Steps to Fix

### 1. Update the production environment variable on the server

```bash
ssh -i C:\Users\smikl\.ssh\lenquant.pem ubuntu@ec2-32-194-123-142.compute-1.amazonaws.com
```

Then edit the docker-compose environment or .env file to add:
```bash
SESSION_COOKIE_DOMAIN=.lenquant.com
```

### 2. Restart the backend container

```bash
cd /path/to/lenquant  # wherever your docker-compose.yml is
docker-compose restart lenquant-backend-1
# OR if using docker compose (v2)
docker compose restart lenquant-backend-1
```

### 3. Clear browser cookies and test

After restarting the backend:
1. Go to `https://sites.lenquant.com`
2. Open browser DevTools → Application → Cookies
3. Delete all cookies for `sites.lenquant.com` and `sites-api.lenquant.com`
4. Log in again with `fern2gue@gmail.com`
5. Verify the cookie `lenquant_session` is now set with domain `.lenquant.com`
6. Dashboard should now load successfully

## Files Changed in This Repo

1. **`.env.example`** - Updated to show the correct `SESSION_COOKIE_DOMAIN` setting
2. **`apps/web/src/lib/api/client.ts`** - Added debug logging for cookie forwarding (can be removed after fix)
3. **`apps/backend/app/api/analytics.py`** - Added error handling (can be kept for better debugging)

## Verification

After applying the fix, check the browser DevTools:
- **Network tab**: Look for the Set-Cookie header in the login response
- **Application tab**: Verify cookie domain shows `.lenquant.com` (with the leading dot)

Backend logs should now show:
```
INFO: POST /api/v1/auth/login HTTP/1.1" 200 OK
INFO: GET /api/v1/analytics/dashboard HTTP/1.1" 200 OK  ✓ (not 401!)
```

## Alternative Solutions (if this doesn't work)

### Option A: Use internal Docker network for SSR
Update `apps/web/src/lib/api/client.ts` to use internal Docker address for server-side requests:
```typescript
const API_BASE_URL = typeof window === "undefined" 
  ? "http://lenquant-backend-1:8000"  // Internal Docker network
  : process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
```

### Option B: Make dashboard client-side
Convert `apps/web/src/app/nsa/page.tsx` to a client component:
```typescript
"use client";

export default function DashboardPage() {
  const [dashboard, setDashboard] = useState(null);
  
  useEffect(() => {
    getAnalyticsDashboard().then(setDashboard);
  }, []);
  
  if (!dashboard) return <div>Loading...</div>;
  // ... rest of component
}
```

## Important Notes

- The allowlist configuration is correct: `fern2gue@gmail.com` is in `AUTH_ALLOWLIST_EMAILS`
- The authentication logic works fine - the issue is purely about cookie sharing
- After fixing, you may want to remove the debug `console.log` statements added to the codebase
