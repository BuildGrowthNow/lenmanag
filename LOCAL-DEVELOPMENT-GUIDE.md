# Local Development Guide: Backend, Frontend, and End-to-End Flow

This guide explains how to run the **backend API**, the **Next.js admin frontend**, and the **Celery worker** locally, how to log in as an operator, and how to go from a raw website URL to a generated preview site.

The commands below assume you run them from the **repo root** (`LenManag`).

---

## 1. Prerequisites

- **Python** 3.11+
- **Node.js** + npm
- **Redis** running locally (for Celery) or `CELERY_TASK_ALWAYS_EAGER=true` in `.env` if you want to avoid running a worker.
- A MongoDB instance configured via `.env` (see `.env.example`).

Copy `.env.example` to `.env` in the repo root and adjust values as needed:

```bash
cp .env.example .env
```

Key settings for local dev:

- `MONGODB_URI` / `MONGODB_DB_NAME` – point to your MongoDB.
- `CELERY_BROKER_URL` – defaults to `redis://localhost:6379/0`.
- `CELERY_TASK_ALWAYS_EAGER=false` – use a real worker. Set to `true` if you want jobs to run inline.
- `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` – backend API base URL.
- `NEXT_PUBLIC_APP_URL=http://localhost:3000` – frontend URL.
- `AUTH_ALLOWLIST_EMAILS` – includes the email you will log in with (e.g. `operator@example.com`).

---

## 2. Start the backend API

From the repo root:

```bash
npm run dev:backend
```

This runs:

```bash
python -m uvicorn app.main:app --reload --app-dir apps/backend
```

By default the backend will listen on:

- **API base URL**: `http://localhost:8000`
- **API prefix**: `/api`

You can verify it is up by visiting:

- `http://localhost:8000/api/health` (if implemented), or
- `http://localhost:8000/docs` for the FastAPI docs.

---

## 3. Start the Celery worker (for background jobs)

If `CELERY_TASK_ALWAYS_EAGER=false` (recommended for realistic testing), you must also run a Celery worker.

In a **separate terminal**, from the repo root:

```bash
cd apps/backend
celery -A app.core.celery_app.celery_app worker -l info
```

This worker will process:

- Extraction jobs
- Brief generation
- Site generation (visual redesign + screenshot QA)

If you prefer to avoid running Redis + Celery during early development, set in your `.env`:

```bash
CELERY_TASK_ALWAYS_EAGER=true
```

In that mode, jobs run inline synchronously inside the API process (good for tests, slower for end-to-end flows).

---

## 4. Start the Next.js admin frontend

From the repo root:

```bash
npm run dev:web
```

This runs the frontend workspace `apps/web`:

- **Frontend URL**: `http://localhost:3000`

Ensure these environment variables in `.env` are consistent:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

The admin shell in the browser talks to the backend through `NEXT_PUBLIC_API_BASE_URL`.

---

## 5. Logging in as an operator

The system uses **allowlist-based auth**. Any email in `AUTH_ALLOWLIST_EMAILS` can log in.

1. Edit `.env` and make sure it includes your email, for example:

   ```env
   AUTH_ALLOWLIST_EMAILS=operator@example.com,admin@example.com
   ```

2. With backend and frontend running, open the admin in your browser:

   - `http://localhost:3000`

3. Use the login UI to authenticate with your allowlisted email.

   - If you want to simulate this programmatically, see `apps/backend/e2e_lenquant_flow.py`, which calls:

     ```http
     POST /api/v1/auth/login
     {
       "email": "operator@example.com",
       "name": "Operator"
     }
     ```

   - The backend sets a `lenquant_session` cookie which the frontend uses for authenticated requests.

---

## 6. End-to-end flow: from URL to generated site

You can follow the flow either via the **admin UI** or directly via the **API** (mirroring `apps/backend/e2e_lenquant_flow.py`). Below is the API-based flow with concrete endpoints; the UI performs the same steps behind the scenes.

### 6.1 Create a lead

Endpoint (after login):

```http
POST /api/v1/leads
Content-Type: application/json

{
  "companyName": "LenQuant",
  "websiteUrl": "https://example.com",  // your target site URL
  "industry": null,
  "notes": null
}
```

- Response contains `data.lead.id` – this `lead_id` is used as the **site id** in later steps.

### 6.2 Start extraction

```http
POST /api/v1/leads/{lead_id}/extraction/start
```

- Response returns a `job` object with `job.id`.
- Poll job status:

  ```http
  GET /api/v1/jobs/{job_id}
  ```

  until `status` is `"completed"` or `"failed"`.

- You can inspect the extraction snapshot:

  ```http
  GET /api/v1/leads/{lead_id}/extraction
  ```

### 6.3 Create and approve a brief

1. Generate a draft brief:

   ```http
   POST /api/v1/leads/{lead_id}/brief
   ```

2. Approve the brief so generation is allowed:

   ```http
   POST /api/v1/leads/{lead_id}/brief/approve
   ```

### 6.4 Generate the visual redesign + site

Trigger generation:

```http
POST /api/v1/sites/{lead_id}/generate
```

- Response returns a `job` with `job.id`.
- Poll status:

  ```http
  GET /api/v1/jobs/{job_id}
  ```

  until `status` becomes `"completed"` or `"failed"`.

Behind the scenes this job will:

- Build a premium section stack with `componentId`s.
- Call Gemini for visual redesign recommendations.
- Render the preview site in Next.js and capture screenshots.
- Run screenshot QA and (if needed) one automatic refinement pass.

### 6.5 View the generated site

Once the generation job completes, fetch the site:

```http
GET /api/v1/sites/{lead_id}
```

- The response body includes fields such as:

  - `previewSlug`
  - `previewUrl`
  - `qualityScore`
  - `readinessStatus`
  - `qaStatus`

You can:

- Open the preview URL directly in your browser:
  - e.g. `http://localhost:3000/sites/{previewSlug}` (or the exact `previewUrl` returned).
- Or navigate via the admin UI review queue to the same preview.

Internally, the frontend route for rendering a generated site is:

- `apps/web/src/app/sites/[slug]/page.tsx`

This uses the `componentId` fields coming from the backend to render the premium sections.

---

## 7. Quick local smoke test (Python script)

For a fully automated end-to-end smoke test, you can run the helper script:

```bash
cd apps/backend
python e2e_lenquant_flow.py
```

This script will:

1. Log in as `operator@example.com` against `BASE_URL = "http://127.0.0.1:8003/api/v1"` (adjust if your API runs on a different port or prefix).
2. Create a lead for `TARGET_URL`.
3. Start and poll the extraction job.
4. Create and approve the brief.
5. Trigger site generation and poll until complete.
6. Print the resulting `previewSlug` and `previewUrl`.

You can use this as a reference for the exact request/response shapes or adapt it to your own local environment (e.g. changing `BASE_URL`, `TARGET_URL`, or the operator email).

---

## 8. Summary of URLs & where to look

- **Frontend admin UI:**
  - `http://localhost:3000`
- **Backend API base:**
  - `http://localhost:8000/api` (with versioned routes under `/api/v1/...`)
- **Generated site preview (example):**
  - `http://localhost:3000/sites/{previewSlug}`
- **Core backend route that renders the preview:**
  - `apps/web/src/app/sites/[slug]/page.tsx`

With this setup you can:

- Log in as an operator.
- Paste a target website URL when creating a lead.
- Run extraction → brief creation → approval → visual redesign + site generation.
- Inspect the resulting premium redesign directly in your browser.
