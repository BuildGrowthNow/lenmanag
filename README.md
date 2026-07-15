# LenQuant Website Fabric

Internal operator shell for lead discovery, preview generation, and handoff.

Phase 1 is the secure admin shell:

- Next.js admin frontend
- Python backend skeleton
- MongoDB connection via environment config
- allowlist-based auth
- protected admin routes
- typed API wrappers
- empty but structured navigation and workspace pages

## Background workers

Discovery, extraction, and generation jobs now run through Celery. For local development:

1. Run Redis (or another broker) accessible at `CELERY_BROKER_URL`.
2. Start the FastAPI app (`uvicorn app.main:app --reload`).
3. Start the worker in a separate shell:

```bash
cd apps/backend
celery -A app.core.celery_app.celery_app worker -l info
```

Setting `CELERY_TASK_ALWAYS_EAGER=true` in `.env` keeps jobs inline for unit tests.

