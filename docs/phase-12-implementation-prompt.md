# Phase 12 Implementation Prompt: Outreach Preparation

## Overview

Phase 12 focuses on the Outreach Preparation workflow - generating message drafts that align with the redesigned site, providing operators with channel-specific messaging capabilities, and integrating the generated site preview and brief context directly into the editing surface.

## Context

Refer to `docs/08-delivery-phases.md` for the complete Phase 6 specification. The goal is to enable operators to generate, review, and customize message drafts for outreach that are tightly coupled to the approved brief and generated site data.

## Status: ✅ COMPLETED

Phase 12 implementation was completed on May 29, 2026.

## Implementation Summary

### Task 1: Enhanced Tone and CTA Controls ✅
- **Backend**: Added `tonePreset`, `customTone`, `ctaVariant`, and `ctaPosition` fields to `MessageDraft` schema
- **Backend**: Added `get_tone_presets()` and `get_cta_variants()` functions with preset options
- **Backend**: Added `GET /api/messages/tone-presets` and `GET /api/messages/cta-variants` endpoints
- **Frontend**: Added `TonePreset` and `CtaVariant` types
- **Frontend**: Added tone selector dropdown, custom tone textarea, CTA variant selector, and CTA position selector in the message workspace

### Task 2: Channel-Specific Delivery States ✅
- **Backend**: Added `deliveryChannel` field with options: whatsapp, linkedin, email, generic
- **Backend**: Added `deliveryStatus` field with states: draft, edited, ready, sent, failed
- **Backend**: Added `get_channel_config()` function with channel-specific settings (character limits, formatting)
- **Backend**: Added status transition methods: `mark_sent()`, `reset_to_draft()`
- **Backend**: Added `GET /api/messages/channels/{channel}/config`, `POST /api/messages/{id}/mark-sent`, `POST /api/messages/{id}/reset-to-draft` endpoints
- **Frontend**: Added `DeliveryChannel` type and updated status badge colors
- **Frontend**: Added channel selector and status transition buttons (Mark Ready, Mark Sent, Reset to Draft)

### Task 3: Copy Review UI with Preview Integration ✅
- **Backend**: Added `PreviewContextResponse` schema and `get_preview_context()` method
- **Backend**: Added `GET /api/messages/{id}/preview-context` endpoint
- **Frontend**: Added `PreviewContextResponse` type and API function
- **Frontend**: Added preview context display showing site preview URL, brief summary, CTAs, Calendly link, and export bundle

### Task 4: Calendly and Link Integration ✅
- **Backend**: Added URL validation for `calendlyUrl` field (validates Calendly domain)
- **Backend**: Link auto-population already implemented in `create_draft` (previewUrl, exportUrl, calendlyUrl)
- **Frontend**: Added Calendly URL input field with validation
- **Frontend**: Added "Insert CTA Link" dropdown to insert Calendly, Preview, or Export links into message body

### Task 5: Message Status Workflow ✅
- **Backend**: Added state machine validation in `mark_ready()` - validates required fields before allowing ready status
- **Backend**: Added state transition validation in `mark_sent()` - only allows ready → sent transition
- **Backend**: Added `validate_ready_status()` method to check subject, body, and CTA requirements
- **Frontend**: Added validation error display when marking as ready fails
- **Frontend**: Added status-based button visibility (Mark Sent only shows when ready, Reset to Draft shows for ready/sent/edited)

## Current State

**What already exists:**
- Message draft repository with lead/brief/site linkage (`apps/backend/app/core/messages.py`)
- NSA messages page with per-lead draft summaries (`apps/web/src/app/nsa/messages/page.tsx`)
- Message drafts workspace component (`apps/web/src/components/message-drafts-workspace.tsx`)
- Basic message generation endpoints
- **NEW**: Tone and CTA controls with presets
- **NEW**: Channel-specific delivery states and status transitions
- **NEW**: Preview context integration
- **NEW**: Calendly and link integration
- **NEW**: Status workflow with validation

**What needs to be done:**
- All Phase 12 tasks completed

## Implementation Tasks

### Task 1: Enhanced Tone and CTA Controls

**Backend:**
- File: `apps/backend/app/schemas/message.py`
  - Extend `MessageDraft` schema with tone presets and CTA configuration fields
  - Add fields: `tonePreset`, `customTone`, `ctaVariant`, `ctaPosition`

- File: `apps/backend/app/core/messages.py`
  - Add `get_tone_presets()` method returning available tone options
  - Add `get_cta_variants()` method returning CTA configuration options
  - Update `generate_message_draft()` to accept tone and CTA parameters

- File: `apps/backend/app/api/messages.py`
  - Add `GET /api/messages/tone-presets` endpoint
  - Add `GET /api/messages/cta-variants` endpoint
  - Update `POST /api/messages` to accept tone and CTA configuration

**Frontend:**
- File: `apps/web/src/lib/types.ts`
  - Update `MessageDraft` type with tone and CTA fields
  - Add `TonePreset` and `CtaVariant` types

- File: `apps/web/src/components/message-drafts-workspace.tsx`
  - Add tone selector dropdown with presets (professional, casual, urgent, friendly)
  - Add custom tone textarea for manual overrides
  - Add CTA variant selector (primary, secondary, tertiary)
  - Add CTA position selector (top, middle, bottom, inline)
  - Show live preview of how tone affects the message

### Task 2: Channel-Specific Delivery States

**Backend:**
- File: `apps/backend/app/schemas/message.py`
  - Add `deliveryChannel` field: "whatsapp" | "linkedin" | "email" | "generic"
  - Add `deliveryStatus` field: "draft" | "edited" | "ready" | "sent" | "failed"
  - Add `channelSpecificConfig` field for channel-specific settings

- File: `apps/backend/app/core/messages.py`
  - Add `update_delivery_status()` method to transition message states
  - Add `get_channel_config()` method returning channel-specific defaults
  - Implement validation rules per channel (character limits, formatting requirements)

- File: `apps/backend/app/api/messages.py`
  - Add `PATCH /api/messages/{id}/status` endpoint for status transitions
  - Add `GET /api/messages/channels/{channel}/config` endpoint

**Frontend:**
- File: `apps/web/src/lib/types.ts`
  - Update `MessageDraft` type with delivery channel and status fields
  - Add `DeliveryChannel` and `DeliveryStatus` types

- File: `apps/web/src/components/message-drafts-workspace.tsx`
  - Add channel selector with channel-specific icons
  - Add status badge showing current delivery state
  - Add channel-specific formatting hints (e.g., WhatsApp character limits)
  - Implement status transition buttons (Draft → Edited → Ready)
  - Add channel-specific preview (simulated WhatsApp/LinkedIn/email view)

### Task 3: Copy Review UI with Preview Integration

**Backend:**
- File: `apps/backend/app/api/messages.py`
  - Update `GET /api/messages/{id}` to include related site preview data
  - Add `GET /api/messages/{id}/preview-context` endpoint returning brief + site snippets

**Frontend:**
- File: `apps/web/src/components/message-drafts-workspace.tsx`
  - Add split-pane view: message editor on left, preview context on right
  - Show site preview thumbnail with link to full preview
  - Show brief summary snippets that informed the message
  - Highlight which sections/CTAs from the site are referenced in the message
  - Add "View full preview" button opening site in new tab
  - Add "View brief" button linking to brief page

- File: `apps/web/src/app/nsa/messages/[id]/page.tsx`
  - Update to use the enhanced message-drafts-workspace component
  - Add breadcrumb navigation back to lead and site

### Task 4: Calendly and Link Integration

**Backend:**
- File: `apps/backend/app/schemas/message.py`
  - Add `calendlyUrl` field to `MessageDraft`
  - Add `previewUrl` field (auto-populated from site)
  - Add `exportBundleUrl` field (if export exists)

- File: `apps/backend/app/core/messages.py`
  - Update `generate_message_draft()` to auto-populate previewUrl from linked site
  - Add logic to detect and include exportBundleUrl if export exists
  - Add Calendly link validation

- File: `apps/backend/app/api/messages.py`
  - Update message endpoints to handle Calendly and link fields

**Frontend:**
- File: `apps/web/src/lib/types.ts`
  - Update `MessageDraft` type with Calendly and link fields

- File: `apps/web/src/components/message-drafts-workspace.tsx`
  - Add Calendly URL input field with validation
  - Add auto-populated preview URL display (read-only, from site)
  - Add export bundle URL display if export exists
  - Add "Insert CTA link" dropdown with options: Calendly, Preview, Export
  - Show link preview when links are inserted

### Task 5: Message Status Workflow

**Backend:**
- File: `apps/backend/app/core/messages.py`
  - Implement state machine for delivery status transitions
  - Add validation: "ready" status requires all required fields
  - Add audit logging for status changes

- File: `apps/backend/app/api/messages.py`
  - Add `POST /api/messages/{id}/mark-ready` endpoint with validation
  - Add `POST /api/messages/{id}/mark-sent` endpoint
  - Add `POST /api/messages/{id}/reset-to-draft` endpoint

**Frontend:**
- File: `apps/web/src/components/message-drafts-workspace.tsx`
  - Add status indicator with visual state (draft = gray, edited = blue, ready = green)
  - Add "Mark as Ready" button (enabled when all required fields filled)
  - Add "Mark as Sent" button (for manual tracking)
  - Add "Reset to Draft" button
  - Show validation errors when trying to mark as ready
  - Add confirmation dialogs for status transitions

## Code Quality Standards

- Follow existing patterns in `apps/backend/app/core/messages.py` and `apps/web/src/components/message-drafts-workspace.tsx`
- Use existing UI components from `apps/web/src/components/ui/`
- Maintain type safety in TypeScript with proper interface definitions
- Add proper error handling and user-friendly error messages
- Include loading states for async operations
- Add validation for user inputs (URLs, character limits, required fields)
- Ensure no code duplication - extract reusable components where appropriate
- Write production-ready code with proper logging and audit trails

## Testing Requirements

- Write unit tests for new backend methods in `apps/backend/tests/`
- Test tone and CTA controls with various combinations
- Test channel-specific validation rules
- Test status transitions with edge cases
- Test Calendly link validation
- Test preview context integration
- Verify responsive UI for split-pane view
- Test error handling for invalid inputs

## Success Criteria

- Operators can select tone presets and see how they affect message drafts
- Channel-specific delivery states are visible and transitionable
- Copy review UI shows actual preview context, not static strings
- Calendly links can be inserted and validated
- Preview and export links are auto-populated from site data
- Status workflow prevents incomplete drafts from being marked ready
- All changes integrate seamlessly with existing message workspace
