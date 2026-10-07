# LenManag / LenQuant Website Fabric — Claude Code Agent Guide

## Project Overview

**LenQuant Website Fabric** is a full-stack SaaS platform that generates, previews, and manages AI-built landing pages. It is a monorepo with three apps:

| App | Stack | Port |
|-----|-------|------|
| `apps/web` | Next.js 15, React 18, TypeScript, Tailwind CSS | 3000 |
| `apps/backend` | Python 3.11+, FastAPI, Celery, MongoDB, Redis | 8000 |
| `apps/compiler` | Node.js, TypeScript (TSX compilation service) | 3001 |

Infrastructure: Docker Compose (prod), MongoDB Atlas + local, Redis, AWS S3, AWS Bedrock (Claude Sonnet), Nginx reverse proxy.

*Important Rule: ALWAYS FOLLOW USER INSTRUCTIONS, DONT DRIFT OR ASSUME OTHER THINGS AND DONT BUILD THINGS THAT THE USER HAVENT SAID, IF YOU NEED CLARIFICATION OR ARE UNSURE OF SOMETHING OR HAVE A BETTER IDEA, TELL THE USER BEFORE STARTING THE TASK*

Never change this: "ignoreDeprecations": "6.0" on tsconfig.

---

## Repository & Deployment

### Git / GitHub
- Remote: `https://github.com/BuildGrowthNow/lenmanag.git`
- **Production deploys automatically** when you push to `main`. GitHub Actions SSHes into EC2, runs `git reset --hard origin/main`, rebuilds Docker images, and restarts containers.
- **Deploy flow:** commit → push to `main` → wait ~5 minutes → GitHub Actions deploys & restarts Docker.

### SSH Access to Production Server
```bash
ssh -i C:\Users\smikl\.ssh\lenquant.pem ubuntu@ec2-32-194-123-142.compute-1.amazonaws.com
```

### Production Paths on Server
```bash
/opt/lenquant/          # project root on EC2
docker compose ps       # check container status
docker compose logs -f backend    # backend logs
docker compose logs -f frontend   # frontend logs
docker compose logs -f compiler   # compiler logs
curl -sf http://localhost:8000/api/v1/health   # backend health
curl -sf http://localhost:3000/                # frontend health
```

### MongoDB Collections
- **`leads`** - Lead/customer information
- **`generated_sites`** - Generated landing page sites (NOT `sites` collection)
- **`jobs`** - Background job tracking
- **`analytics_events`** - Analytics data

### Production URLs
- Frontend: `https://sites.lenquant.com`
- Backend API: `https://sites-api.lenquant.com`
- Preview sites: `https://sites.lenquant.com/st/<slug>`

---

## Development Commands

### Root (monorepo)
```bash
npm run dev              # start Next.js frontend
npm run dev:web          # same, explicit
npm run dev:backend      # start FastAPI with hot reload
npm run lint:web         # ESLint on frontend
```

### Frontend (`apps/web`)
```bash
cd apps/web
npm run dev              # Next.js dev server
npm run build            # production build (must pass cleanly)
npm run lint             # ESLint (zero warnings/errors required)
npx tsc --noEmit         # Pyright/Pylance equivalent for TypeScript
```

### Backend (`apps/backend`)
```bash
cd apps/backend
python -m uvicorn app.main:app --reload    # dev server
python -m pytest tests/                   # run tests
python -m ruff check .                    # lint (zero issues required)
python -m ruff format .                   # auto-format
python -m pyright .                       # type checking (zero issues required)
```

### Compiler (`apps/compiler`)
```bash
cd apps/compiler
npm run build            # compile TypeScript
npm run dev              # dev mode
```

### Docker (local)
```bash
docker compose up --build        # build and start all services
docker compose down              # stop services
docker compose logs -f           # stream logs
```

---

## Code Quality Rules — Non-Negotiable

After **every task**, run the full quality suite across the entire platform and fix all issues before committing:

### Frontend checks
```bash
cd apps/web && npm run lint          # zero ESLint warnings or errors
cd apps/web && npm run build         # must succeed cleanly
cd apps/web && npx tsc --noEmit      # zero TypeScript errors
```

### Backend checks
```bash
cd apps/backend && python -m ruff check .     # zero ruff warnings or errors
cd apps/backend && python -m ruff format .    # apply formatting
cd apps/backend && python -m pyright .        # zero pyright issues
```

### Rules
- **No lint warnings or errors** anywhere — fix them, don't suppress them
- **No TypeScript `any` types** unless genuinely unavoidable (document why)
- **No unused imports, variables, or dead code**
- **No `TODO`, `FIXME`, placeholder comments, or stub implementations** in committed code
- **No legacy code** — remove deprecated patterns immediately
- **Production-ready code only** — every commit to `main` goes live
- Maintain all existing logic when refactoring; don't accidentally remove features
- Both frontend and backend must be in sync — if you change an API contract, update both sides

---

## Architecture

### Frontend (`apps/web/src/`)
```
app/                    # Next.js App Router pages
  (app)/                # Authenticated app routes (/app/*)
  (public)/             # Public marketing routes
  st/[slug]/            # Public site preview pages
api/                    # Next.js API routes (auth, stripe, email)
components/             # Shared React components
lib/                    # Utilities, types, constants, API client
  api.ts                # Backend API client
  auth.ts               # JWT auth helpers
  types.ts              # Shared TypeScript types
  constants.ts          # App-wide constants
```

Authentication: JWT stored in `localStorage`, validated client-side. Middleware does not enforce auth (browser navigations handled by client layout). Auth pages: `/login`, `/signup`, `/verify-email`.

### Backend (`apps/backend/app/`)
```
main.py                 # FastAPI app entry, middleware, CORS
api/                    # Route handlers
  router.py             # API router aggregation
  auth.py               # /auth/* endpoints
  sites.py              # /sites/* endpoints
  jobs.py               # /jobs/* endpoints
  leads.py              # /leads/* endpoints
  assets.py             # /assets/* endpoints
  admin.py              # /admin/* endpoints
  health.py             # /health endpoint
core/                   # Business logic, config, DB, LLM clients
schemas/                # Pydantic request/response models
```

API prefix: `/api/v1/`  
LLM: AWS Bedrock (Claude Sonnet) in production, Gemini in local dev (set `LLM_PROVIDER` env var).  
Background tasks: Celery + Redis.  
Database: MongoDB (Motor async driver).

### Compiler (`apps/compiler/src/`)
Internal service that compiles TSX component strings into deployable HTML/JS. Called by the backend at `http://compiler:3001`.

---

## Environment Variables

Key variables (see `.env.example` for full list):

| Variable | Description |
|----------|-------------|
| `MONGODB_URI` | MongoDB connection string |
| `MONGODB_DB_NAME` | Database name (default: `lenmanag`) |
| `SESSION_SECRET` | Express session secret |
| `JWT_SECRET` | JWT signing key |
| `NEXT_PUBLIC_API_BASE_URL` | Backend URL for frontend (public) |
| `NEXT_PUBLIC_APP_URL` | Frontend app URL (public) |
| `LLM_PROVIDER` | `bedrock` (prod) or `gemini` (local) |
| `BEDROCK_MODEL_ID` | `us.anthropic.claude-sonnet-4-6-v1` |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | AWS credentials |
| `CELERY_BROKER_URL` | Redis URL for Celery |
| `RESEND_API_KEY` | Transactional email (Resend) |
| `NEXT_PUBLIC_STRIPE_PAYMENT_LINK` | Stripe payment link |

Production env file lives at `/opt/lenquant/.env.production` on the EC2 server (preserved across deploys via `git clean -e .env.production`).

---

## Authentication & API Testing

### Backend Authentication System

The backend uses a **password + email allowlist** system for operator access (no user registration):

**Allowlist Configuration** (from `.env.production`):
```
AUTH_ALLOWLIST_EMAILS=admin@example.com,fern2gue@gmail.com
AUTH_ALLOWLIST_DOMAINS=lenquant.com,lengrowth.com,sites.lenquant.com
AUTH_ADMIN_PASSWORD=LENGROWTH2026
```

Only emails in the allowlist or domains in the allowlist can authenticate. All use the same shared password.

### AI Agent Test Credentials

**Two service accounts exist for Claude AI Agents and automated testing:**

#### ops-agent (created 2026-07-20)

| Field | Value |
|-------|-------|
| **Email** | `ops-agent@lenquant.internal` |
| **Password** | `LQ$opsAgent2026!Internal#Only` |
| **User ID** | `6a5e6f1750e1773f8fc48d33` |
| **Endpoint** | `POST /api/v1/users/login` |
| **Verified** | Yes |
| **Token Type** | JWT Bearer |

#### ai-agent (original)

**For Claude AI Agents and automated testing**, a dedicated user account exists in MongoDB:

| Field | Value |
|-------|-------|
| **Email** | `ai-agent@lenquant.internal` |
| **Password** | `LQ$aiAgent2026!Secure#TestOnly` |
| **User ID** | `6a59e2aca2a1aebf9b7dd127` |
| **Endpoint** | `POST /api/v1/users/login` |
| **Verified** | Yes |
| **Token Type** | JWT Bearer |
| **Database** | MongoDB Atlas (`lenmanag` database) |

**Usage:**
```bash
# AI agent login (returns JWT access token, not session cookie)
curl -X POST "http://localhost:8000/api/v1/users/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "ai-agent@lenquant.internal",
    "password": "LQ$aiAgent2026!Secure#TestOnly"
  }'

# Response format:
{
  "status": "success",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "user": {
      "id": "6a59e2aca2a1aebf9b7dd127",
      "email": "ai-agent@lenquant.internal",
      "is_verified": true,
      "created_at": "2026-07-17T08:07:08.822000",
      "updated_at": "2026-07-17T08:07:09.315000"
    }
  },
  "error": null
}

# Use JWT token in Authorization header:
curl -H "Authorization: Bearer <access_token>" \
  "http://localhost:8000/api/v1/users/me"
```

**Notes:**
- This account uses the `/users/login` endpoint (JWT-based), **not** `/auth/login` (session-based)
- JWT tokens expire after 7 days (168 hours)
- Password is bcrypt-hashed in MongoDB
- To recreate user (with proper MongoDB connection):
  ```bash
  cd C:/Users/smikl/Desktop/Work/LenManag && \
  export MONGODB_URI="mongodb+srv://fern2gue:hJk7CDkZuwssFDz4@lenmanag.zzbkrv.mongodb.net/" && \
  export MONGODB_DB_NAME="lenmanag" && \
  python apps/backend/create_test_user.py
  ```

**Quick Token Retrieval (for AI agents):**
```bash
# Use the helper script to get a token quickly
cd apps/backend && python get_ai_agent_token.py

# Output includes ready-to-use export command:
# export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
# curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/users/me
```

**Complete Working Example:**
```bash
# Step 1: Login and extract JWT token
RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/users/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "ai-agent@lenquant.internal",
    "password": "LQ$aiAgent2026!Secure#TestOnly"
  }')

# Extract access_token from JSON response (requires jq, or parse manually)
TOKEN=$(echo "$RESPONSE" | python -c "import sys, json; print(json.load(sys.stdin)['data']['access_token'])")

# Step 2: Use token for authenticated requests
# Get current user info
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/users/me"

# Access any protected endpoint (example: list leads if implemented)
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/leads?limit=10"
```

### How to Authenticate for API Testing

#### Step 1: Get Session Cookie

```bash
# Login to get session token
RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "fern2gue@gmail.com", "password": "LENGROWTH2026"}')

# Extract session cookie from response
SESSION=$(echo "$RESPONSE" | grep -o 'lenquant_session=[^;]*' | cut -d'=' -f2)
```

**Alternative:** Get it from response headers:
```bash
curl -v -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "fern2gue@gmail.com", "password": "LENGROWTH2026"}' 2>&1 | grep -i "set-cookie"

# Output will show:
# set-cookie: lenquant_session=eyJlbWFpbCI6ImZlcm4yZ3VlQGdtYWlsLmNvbSIs...; ...
```

#### Step 2: Use Session Cookie in API Calls

Store the cookie and use it in all authenticated requests:

```bash
SESSION="eyJlbWFpbCI6ImZlcm4yZ3VlQGdtYWlsLmNvbSIsIm5hbWUiOiJmZXJuMmd1ZSIsInJvbGUiOiJvcGVyYXRvciIsImlhdCI6MTc4NDIwMTU4MSwiZXhwIjoxNzg0MjMwMzgxfQ.7weDRjJ9rB6sJkTrx9pOjWcBiBj9YBWODO_0eRjZlYI"

# Example: Create a lead
curl -s -X POST -H "Cookie: lenquant_session=$SESSION" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Lead",
    "email": "test@example.com",
    "phone": "+1-555-0123",
    "companyName": "Test Company",
    "websiteUrl": "https://example.com",
    "industry": "Technology",
    "targetAudience": "Business users"
  }' \
  "http://localhost:8000/api/v1/leads" | jq .

# Example: List leads
curl -s -H "Cookie: lenquant_session=$SESSION" \
  "http://localhost:8000/api/v1/leads?limit=25" | jq .

# Example: Start extraction
curl -s -X POST -H "Cookie: lenquant_session=$SESSION" \
  "http://localhost:8000/api/v1/leads/{lead_id}/extraction/start" | jq .

# Example: Create master brief
curl -s -X POST -H "Cookie: lenquant_session=$SESSION" \
  "http://localhost:8000/api/v1/leads/{lead_id}/master-brief" | jq .
```

### Authentication Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/auth/login` | POST | Authenticate and get session token |
| `/api/v1/auth/verify` | POST | Check if email is allowlisted (no password needed) |
| `/api/v1/auth/session` | GET | Get current session info |
| `/api/v1/auth/refresh` | POST | Refresh session token |
| `/api/v1/auth/logout` | POST | Logout and invalidate session |

### Testing Authenticated Endpoints

**Full workflow example** for testing lead → extraction → brief → generation:

```bash
#!/bin/bash

# 1. Login
SESSION=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "fern2gue@gmail.com", "password": "LENGROWTH2026"}' \
  | jq -r '.data | @base64 | @json' | tr -d '"')

# 2. Create lead
LEAD=$(curl -s -X POST -H "Cookie: lenquant_session=$SESSION" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Lead",
    "email": "test@example.com",
    "companyName": "Test Company",
    "websiteUrl": "https://example.com"
  }' \
  "http://localhost:8000/api/v1/leads")

LEAD_ID=$(echo "$LEAD" | jq -r '.data.lead.id')
echo "Created lead: $LEAD_ID"

# 3. Start extraction
curl -s -X POST -H "Cookie: lenquant_session=$SESSION" \
  "http://localhost:8000/api/v1/leads/$LEAD_ID/extraction/start" | jq .

# 4. Wait for extraction to complete (check Celery logs)
sleep 60

# 5. Create master brief
curl -s -X POST -H "Cookie: lenquant_session=$SESSION" \
  "http://localhost:8000/api/v1/leads/$LEAD_ID/master-brief" | jq .

# 6. Approve brief
curl -s -X POST -H "Cookie: lenquant_session=$SESSION" \
  -H "Content-Type: application/json" \
  -d '{"approvedBy": "fern2gue@gmail.com", "notes": "Auto-approved"}' \
  "http://localhost:8000/api/v1/leads/$LEAD_ID/master-brief/approve" | jq .

# 7. Trigger site generation
curl -s -X POST -H "Cookie: lenquant_session=$SESSION" \
  -H "Content-Type: application/json" \
  -d '{"force": true}' \
  "http://localhost:8000/api/v1/sites/$LEAD_ID/generate" | jq .
```

### Important Notes

- **Session tokens expire** after the time set in `SESSION_COOKIE_MAX_AGE_SECONDS` (default: 8 hours)
- **Cookies are HttpOnly** and Secure — must be passed via `Cookie` header, not JavaScript
- **Password is shared** across all allowlisted operators — no per-user passwords
- **Public endpoints** (site preview at `/api/v1/public/st/{slug}`) don't require authentication
- For **production testing**, use credentials from `.env.production` on the server

### Common Issues

| Problem | Solution |
|---------|----------|
| 401 Unauthorized | Session expired or missing. Re-authenticate. |
| Cookie not persisting | Make sure you're using `-c` flag with curl: `curl -c /tmp/cookies.txt ...` |
| API returns 404 for authenticated endpoint | Check session is valid, use GET `/api/v1/auth/session` to verify |
| "Authentication required" on POST | Session cookie must be in `Cookie` header, not `Authorization` header |

---

## Workflow for Every Task

1. **Understand the scope** — read relevant files before making changes
2. **Make changes** — frontend and backend in sync if API contract changes
3. **Run all quality checks** — fix every lint, ruff, build, pyright, and pylance issue across the entire platform
4. **Remove all dead code** — no TODOs, no placeholders, no legacy patterns
5. **Commit and push to `main`** — triggers auto-deploy via GitHub Actions
6. **Verify deployment** — wait ~5 minutes, then SSH into server and check:
   ```bash
   ssh -i C:\Users\smikl\.ssh\lenquant.pem ubuntu@ec2-32-194-123-142.compute-1.amazonaws.com
   cd /opt/lenquant && docker compose ps
   curl -sf http://localhost:8000/api/v1/health
   curl -sf http://localhost:3000/
   ```

---

## Docker Services Summary

| Service | Image | Container | Internal Port |
|---------|-------|-----------|---------------|
| frontend | `./apps/web` | `lenquant-frontend` | 3000 |
| backend | `./apps/backend` | `lenquant-backend` | 8000 |
| compiler | `./apps/compiler` | `lenquant-compiler` | 3001 |
| redis | `redis:7-alpine` | `lenquant-redis` | 6379 |
| mongodb | `mongo:7` | `lenquant-mongodb` | 27017 |

All services share the `lenquant-network` bridge network.

---

## Agent Behaviour

- **Work sequentially, never in parallel** — do not spawn sub-agents or run parallel tool calls that hit the LLM. AWS Bedrock has strict requests-per-minute limits; parallel agent tasks will cause rate-limit errors. Always complete one step fully before starting the next.

---

## Important Conventions

- **Never commit secrets** — use `.env` locally, GitHub Actions secrets in CI
- **Never commit `.env`** — it is in `.gitignore`
- **Subdomain routing**: `sites.*` → public site previews, no auth; everything else → app with auth
- **Pydantic v2** is used in the backend — use `model_validator`, `field_validator`, not v1 validators
- **Next.js App Router** — no `pages/` directory, use `app/` with layouts and server components
- **Tailwind CSS** — utility-first, no inline styles, use `cn()` from `lib/utils.ts` for conditional classes
- **Error handling** — always handle async errors, never silent catches

## TypeScript Configuration

- **baseUrl deprecation**: The `baseUrl` compiler option is deprecated in TypeScript and will stop functioning in TypeScript 7.0. To silence the deprecation warning, add `"ignoreDeprecations": "6.0" - never change it to 5.0` to the `compilerOptions` in `tsconfig.json`. Do NOT change the baseUrl version to 5.0 or remove baseUrl — keep the current configuration and only add the ignoreDeprecations flag.
