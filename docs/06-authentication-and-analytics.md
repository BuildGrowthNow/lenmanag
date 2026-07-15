# Authentication and Analytics

## Authentication Model

The master system should use simple internal authentication controlled by an allowlist of approved email addresses defined in environment configuration.

## Access Rules

Only users whose email exists in the approved email list may access the admin system.

Recommended behavior:

- on login, verify the email against the allowlist
- deny access if the email is not approved
- allow session creation only after allowlist validation succeeds
- optionally restrict by domain if needed later, but treat explicit allowlist as the source of truth

## Minimum Auth Flow

1. User enters email.
2. System sends or verifies a login step.
3. Backend checks the email against the approved environment list.
4. If approved, create a session.
5. If denied, show a clean access denied state.

## Environment Configuration

The allowlist should be provided through environment-level configuration, such as:

- approved admin emails
- optional fallback admin domain rules
- session secret
- analytics secret
- internal app base URL

## Auth Security Goals

- prevent unauthorized access to the master control plane
- keep auth simple enough to maintain
- avoid user self-registration
- log all failed and successful login attempts

## Analytics Requirements

Analytics must answer operational questions, not vanity questions.

The system should track:

- preview page views
- unique visits by session
- CTA clicks
- outbound link clicks
- Calendly clicks
- scroll depth or major content exposures
- time on page
- referrer and campaign source
- message-to-visit attribution when available
- source site comparison after preview rendering
- source website, brief, and generated output review actions in admin

## Analytics Collection Points

### Preview Site Events

Generated sites should emit events for:

- page view
- hero CTA click
- secondary CTA click
- contact click
- calendly click
- section exposure
- form interaction if present

### Admin Events

The admin should track:

- lead created
- lead imported
- site generated
- site republished
- site override applied
- site export created
- message draft edited
- message marked ready
- site opened from admin
- brief approved
- brief edited
- theme variant changed
- generation regenerated

## Analytics Storage Rules

- store raw events in MongoDB
- preserve timestamps and source metadata
- avoid overwriting event history
- support aggregated queries for dashboard use

## Analytics Dashboards

The admin analytics surface should show:

- leads with visits but no CTA clicks
- leads with CTA clicks but no booked calls
- best-performing generated site variants
- message performance by channel when sending exists
- traffic sources and referrers

## Future-Proofing

The analytics model should leave room for:

- future message send automation
- A/B testing of hero variants
- outreach source attribution
- conversion funnel reporting

## Implementation status

**Checklist**

- [x] Email allowlist auth implemented via FastAPI routes with audit logging and session cookies (`apps/backend/app/api/auth.py`).
- [x] Next.js login form + middleware enforce the session requirement before allowing access to `/nsa` (`apps/web/src/app/login/login-form.tsx`, `apps/web/middleware.ts`).
- [x] Session cookies are hardened for production and can be refreshed via `/api/auth/refresh` with configurable `secure`, `samesite`, domain, and max-age settings.
- [x] Analytics repository code, ingestion endpoints, client instrumentation, and the `/nsa/analytics` dashboard are wired end-to-end.
- [x] Admin events (lead create/merge/import, brief lifecycle, overrides, exports, messages, etc.) stream into analytics so operators can audit actions alongside preview telemetry.

**Details**

Authentication now sets `secure` session cookies (configurable via `.env`) and exposes a refresh route so long-lived operator sessions stay valid without re-login. Analytics events are ingested from previews, admin actions, and dashboards; the NSA analytics page renders the same aggregates returned by `/api/analytics/dashboard` and surfaces per-site/lead metrics sourced from `app/core/analytics.py`.
