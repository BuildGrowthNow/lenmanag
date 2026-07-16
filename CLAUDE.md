# LenManag / LenQuant Website Fabric — Claude Code Agent Guide

## Project Overview

**LenQuant Website Fabric** is a full-stack SaaS platform that generates, previews, and manages AI-built landing pages. It is a monorepo with three apps:

| App | Stack | Port |
|-----|-------|------|
| `apps/web` | Next.js 15, React 18, TypeScript, Tailwind CSS | 3000 |
| `apps/backend` | Python 3.11+, FastAPI, Celery, MongoDB, Redis | 8000 |
| `apps/compiler` | Node.js, TypeScript (TSX compilation service) | 3001 |

Infrastructure: Docker Compose (prod), MongoDB Atlas + local, Redis, AWS S3, AWS Bedrock (Claude Sonnet), Nginx reverse proxy.

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
