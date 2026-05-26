# Product Vision

## Purpose

Build an internal platform for selling websites and landing pages by turning leads into high-quality, conversion-focused redesigns with accompanying outreach materials.

The system should:

- ingest single URLs or bulk CSV lead lists
- detect or confirm the lead website
- crawl public site content and sitemap data
- extract brand signals, messaging, structure, and page content
- generate a custom redesign that uses the lead's own branding
- provide a preview site for internal review and outreach
- generate contextual outreach copy for future LinkedIn, WhatsApp, and email campaigns
- track analytics for preview engagement and outreach performance
- let the operator safely improve a site before a meeting or before sending a message
- preserve manual edits as tracked overrides instead of overwriting them during regeneration

## Operator Workflow

This system is designed for a single operator or small team using it as a sales and fulfillment machine.

The typical loop is:

1. import a lead or enter a URL after a meeting
2. crawl the public site and generate a brief
3. generate a preview site and outreach assets
4. inspect the preview locally or in the browser
5. apply manual edits as explicit overrides
6. regenerate from the stored spec and overrides
7. export or share the updated preview
8. use the preview in the next conversation or message

## Non-Negotiable Product Principles

The generated output must not feel generic.

Every site should:

- use the lead's own logo, colors, and branding cues when available
- adapt tone and content to the lead's likely buyers
- avoid placeholder language entirely; if the source site is sparse, show the gap in admin and generate the strongest source-grounded alternative available
- vary hero layouts, section sequencing, and motion treatment
- feel premium and conversion-aware at the same time
- use public HTML and public assets only unless the source explicitly provides more
- feel like an improved version of the original business, not a generic template

The platform is not a generic landing page generator. It is a redesign and sales enablement machine.

## Target Workflow

1. Import leads through CSV, manual URL entry, or future CRM sync.
2. Resolve the target website for each lead.
3. Crawl the site and sitemap.
4. Extract:
   - homepage structure
   - services or product positioning
   - contact and CTA patterns
   - branding cues
   - public assets
   - metadata and social signals
   - page-level content summaries
   - inferred audience and conversion intent
5. Generate:
   - a redesigned website preview
   - a rewritten CTA strategy
   - outreach copy tailored to the company and audience
6. Review the result in the admin system.
7. Send or prepare messages using future automation tools.
8. Track visits, engagement, and conversion signals.

## Success Criteria

The product succeeds when it can:

- process many leads in bulk without manual rebuilding
- generate better-looking versions quickly enough to support outreach at scale
- show internal users exactly what was generated and why
- support future message automation without redesigning the stack
- prove whether preview pages are being visited and acted on
- produce consistently distinct sites across a batch, even when the source sites are similar
- let operators see both the raw source material and the interpreted design decisions

## Scope Boundary

This system should focus on:

- lead intake
- website intelligence
- premium redesign generation
- preview hosting
- outreach preparation
- analytics
- internal admin access

It should not initially try to solve:

- full CRM replacement
- payment processing for subscriptions
- public self-serve site building
- multi-tenant client editing portals

## Core Product Choice

The system should be one reusable website fabric, not one separate Next.js app per lead.

That means:

- one codebase for the admin and preview runtime
- many data-driven company sites generated from shared templates and variant rules
- site-specific content, branding, and layout choices stored as data
- future static or edge deployment options derived from the same generator
- manual edits stored as durable overrides so regenerated output stays in sync with operator changes
