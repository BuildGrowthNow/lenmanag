# API Contract

## Contract Principles

The frontend should only depend on documented backend responses.

The backend should only return shapes that the frontend can render without guesswork.

## Core Resource Groups

### Auth

- login request
- login verification
- session status
- logout
- `POST /api/auth/login`
- `POST /api/auth/verify`
- `GET /api/auth/session`
- `POST /api/auth/logout`
- `POST /api/auth/refresh`

### Leads

- create lead
- bulk import leads
- list leads
- get lead detail
- update lead metadata
- delete or archive lead
- `POST /api/leads`
- `POST /api/leads/import`
- `GET /api/leads`
- `GET /api/leads/:id`
- `PATCH /api/leads/:id`
- `DELETE /api/leads/:id`

### Extraction

- start crawl
- get crawl status
- get extraction snapshot
- list discovered pages
- refresh crawl
- `POST /api/leads/:id/extraction/start`
- `GET /api/jobs/:id`
- `GET /api/leads/:id/extraction`
- `GET /api/leads/:id/pages`
- `POST /api/leads/:id/extraction/refresh`

### Briefing

- create site brief
- get site brief
- update site brief notes
- approve site brief
- `POST /api/leads/:id/brief`
- `GET /api/leads/:id/brief`
- `PATCH /api/leads/:id/brief`
- `POST /api/leads/:id/brief/approve`

### Generation

- start generation
- get generation status
- list site versions
- get generated site detail
- republish preview
- compare generated versions
- get theme variants
- `POST /api/sites/:id/generate`
- `GET /api/sites/:id`
- `GET /api/sites/:id/versions`
- `GET /api/themes`
- `GET /api/sites/:id/compare`
- `POST /api/sites/:id/republish`

Notes:
- The generator honors structured site overrides. If an active override is saved with `path: "themeKey"`, the generation pass will use that theme as authoritative, recompute brand tokens and section/hero baselines for the selected theme, and persist `themeKey`, `themeName`, and `themeRationale` on the generated site and version documents. The `themeRationale` will be set to a clear operator message such as "Operator selected theme <name>".

### Editing and Export

- create or update structured overrides
- list overrides
- delete or disable an override
- export a site snapshot
- get export status
- `POST /api/sites/:id/overrides`
- `GET /api/sites/:id/overrides`
- `PATCH /api/sites/:id/overrides/:overrideId`
- `DELETE /api/sites/:id/overrides/:overrideId`
- `POST /api/sites/:id/export`
- `GET /api/sites/:id/export`

### Messaging

- create draft
- update draft
- list drafts
- mark ready
- copy draft by channel
- `POST /api/leads/:id/messages`
- `GET /api/leads/:id/messages`
- `PATCH /api/messages/:id`
- `POST /api/messages/:id/ready`
- `GET /api/messages/:id/copy?channel=...`

### Analytics

- ingest event
- query site metrics
- query lead metrics
- query dashboard aggregates
- `POST /api/analytics/events`
- `GET /api/analytics/sites/:id`
- `GET /api/analytics/leads/:id`
- `GET /api/analytics/dashboard`

### Review and QA

- compare source site to generated output
- mark site quality reviewed
- record generation feedback
- `GET /api/sites/:id/review`
- `POST /api/sites/:id/review`
- `POST /api/sites/:id/review/compare`
- `PATCH /api/sites/:id/review`

## Response Design Rules

Every response should include enough information for the UI to be predictable.

Recommended response properties:

- `id`
- `status`
- `createdAt`
- `updatedAt`
- `error`
- `progress`
- `items`
- `pagination`
- `sourceReferences`
- `confidence`
- `version`
- `brandTokens`
- `reviewState`
- `previewUrl`
- `themeKey`
- `jobId`
- `missingRequirements`
- `readinessStatus`
- `gapItems`
- `placeholderRisk`
- `overrideStatus`
- `exportStatus`

## UI Mapping Expectations

The frontend should map API groups as follows:

- dashboard cards from aggregate endpoints
- tables from list endpoints
- detail drawers from resource detail endpoints
- charts from analytics aggregate endpoints
- previews from generated site detail endpoints
- brand evidence panels from extraction and brief endpoints
- review states from QA endpoints
- preview screenshots and comparisons from generation review endpoints
- missing-field panels from extraction, brief, and generation endpoints
- production-readiness badges from generation and review endpoints

## Placeholder Policy

The API should never return placeholder content as if it were production data.

If source information is missing, the API should return explicit gap data such as:

- missing content fields
- missing brand assets
- low-confidence inferred fields
- QA blockers
- required manual review items

The frontend should use these responses to show what must be fixed, not to hide the gap behind filler content.

## Versioning

API contracts should be versioned when stable enough to freeze.

Recommended approach:

- keep internal endpoints versioned by route namespace or explicit schema version
- avoid silent response shape changes
- preserve older preview records so existing generated sites do not break

**Current implementation**

- All routes are exposed under `/api/v1/*` and require either the `X-API-Version: 1` header or an `Accept` header of `application/vnd.lenmanag.v1+json`.
- Requests without a supported version receive `406 Not Acceptable`, protecting the contract from accidental drift.
- Clients can still opt into future versions by changing the version header while older UIs keep working against their original namespace.

## Response Envelope

Every JSON response now shares a consistent envelope:

```
{
  "status": "success",
  "meta": {
    "version": "v1",
    "requestId": "...",
    "generatedAt": "2026-05-29T14:45:10Z"
  },
  "data": { ...payload... }
}
```

- `status` differentiates success and error flows.
- `meta.version` echoes the negotiated API version so clients can log/trace compatibility.
- `requestId` enables correlating UI events with backend logs.
- Errors use the same envelope with `status: "error"` and an `error` object describing the failure.

## Implementation status

**Checklist**

- [x] FastAPI routers expose the documented auth, leads, jobs, sites, messages, and themes endpoints (`apps/backend/app/api/*`).
- [x] Frontend API client functions consume those endpoints with typed responses (`apps/web/src/lib/api/*`).
- [x] Extraction refresh, generation, review, override, export, and analytics endpoints listed here are implemented and power the NSA UI.
- [x] No versioning strategy is enforced—routes are all under `/api` without schema version negotiation.
- [x] Response envelopes vary per endpoint (some return plain objects, others wrap in `{ "job": ... }`), so consistency work remains.

**Details**

The implemented endpoints now satisfy Phase 1–3 workflows (auth, lead intake, crawling, site/brief read/write, job polling, messaging) and ship behind a negotiated `/api/v1` namespace. Override CRUD, export, analytics, review, public preview, and messaging responses all emit the unified `ResponseEnvelope`, so admin and preview clients share the same parsing logic, and backend logs can trace each request with the emitted `meta.requestId` while guarding against undetected schema drift.
