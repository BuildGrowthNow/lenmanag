# Landing Page Upgrade: 5-Phase Implementation Guide

**Project**: LenQuant Website Fabric Landing Page Redesign  
**Version**: 1.0  
**Date**: 2026-07-16  
**Status**: Implementation Ready

---

## Executive Summary

This document outlines a comprehensive 5-phase upgrade to the LenQuant landing page at `https://sites.lenquant.com`. The redesign modernizes the user experience through interactive navigation, enhanced hero section with animated mockups, value-focused feature presentation, refined pricing structure, and professional footer with company information.

**Key Changes**:
- Add sticky navigation menu with smooth scroll to sections
- Replace floating browser mockups with animated screen mockup and confetti effect
- Add screenshot carousel with opacity transitions (from Awwwards)
- Create dynamic "Trusted By" section with custom SVG logos
- Redesign "Everything Included" section with solar system visual (circle with interactive points)
- Move process timeline below icons to center
- Clean up technical language across all sections
- Restructure pricing with grouped cards and dropdown for extra services
- Add maintenance service ($500/hour meeting + 3 tasks/month)
- Add hosting service ($200/month, separate from professional website delivery)
- Add visual distinction between one-time and recurring pricing
- Remove dashes/em-dashes from testimonials and FAQ
- Enhance footer with address, phone, and company link

---

## Phase 1: Navigation & Hero Section Enhancement

### 1.1 Top Banner  Fix
**File**: `apps/web/src/components/landing/social-proof-ticker.tsx`

**Requirements**:
- Fix to banner appear on top of the navbar (not behind it or above it)


**Deliverables**:
- Banner displays on top navbar without being hidden
- No visual overlap issues

---

### 1.2 Hero Section Cleanup
**File**: `apps/web/src/app/page.tsx` (Hero Section)

**Requirements**:
- **REMOVE**: "Premium Website Generation" badge with sparkles icon
- **REMOVE**: FloatingMockup component (floating screens serve no purpose)
- **REMOVE**: ScreenshotCarousel component (we don't have real examples to show)
- Keep: AnimatedHeroHeadline, AnimatedStats, CTA button

**Deliverables**:
- Cleaner hero section
- No unnecessary floating elements
- No fake screenshot carousel

---

### 1.3 Typing Animation Hero Headline
**File**: `apps/web/src/components/landing/animated-hero-headline.tsx`

**Current State**: Static fade-in animation showing "Master Design • $1,000 • 3 Days"

**New Requirements**:
- Create typing animation effect, static it will always be: 
  "Your Website" below it:
- Sequence should type:
  2. "In 3 Days"  
  3. "$1,000"
  4. "with a Master Design"
- Each phrase should type out character by character on the second line
- Cursor blink effect while typing
- Clean, modern typography
- Mobile responsive sizing

**Animation Sequence**:
2. Type "In 3 Days" (pause)
3. Type "$1,000" (pause)
4. Type "Master Design" (pause)
5. All text remains visible

**Deliverables**:
- Typing animation component
- Character-by-character reveal
- Responsive text sizing
- Smooth cursor animation

---

## Phase 2: Social Proof & Features

### 2.1 Trusted Companies Section - Horizontal Layout
**File**: `apps/web/src/components/landing/trusted-companies.tsx`

**Current State**: Large vertical cards with logos and descriptions

**New Requirements**:
- Make section SMALLER in height
- Horizontal layout: Logo + Company Name side by side
- Remove descriptions and extra text
- Simple, clean presentation
- Title: "Trusted by Forward-Thinking Companies"

**Layout Structure**:
```
[Logo Icon] Company Name    [Logo Icon] Company Name    [Logo Icon] Company Name
```

**Design Specifications**:
- Logo size: 32px x 32px (smaller than current)
- Company name in simple text next to logo
- Horizontal flex layout
- Responsive: wrap to multiple rows on mobile
- Minimal spacing and padding
- No background cards or borders
- improve the svgs of the logos 

**Deliverables**:
- Smaller, horizontal trusted companies section
- Logo + name pairs only
- No descriptions or marketing copy
- Height reduced by ~50%

---

### 2.2 Value-Focused Features Section
**File**: `apps/web/src/components/landing/features-solar-system.tsx` (replaces bento-features.tsx)

**Requirements**:
- Replace flat grid layout with "solar system" visualization
- Central circle with company value proposition
- 6-8 points orbiting around the center (like planets) - i just see 1 right now
- Interactive: hover over a point to see tooltip/popover
- Non-technical language focusing on benefits, not features
- Smooth rotation animation

**Feature Points** (examples, adjust as needed):
- Center: "Everything You Need for Your Online Presence"
- Orbit 1: Beautiful Design (visual appeal, brand identity)
- Orbit 2: Fast Loading (better user experience, SEO benefits)
- Orbit 3: Mobile Ready (reach customers on any device)
- Orbit 4: Easy to Manage (no coding required, simple updates)
- Orbit 5: Customer Support (always here when you need help)
- Orbit 6: Professional Quality (trusted by successful businesses)
- Orbit 7: Quick Turnaround (ready in just 3 days)
- Orbit 8: Affordable (get enterprise-quality without premium price)

**Visualization**:
```
                    [Point 1]
           [Point 8]              [Point 2]
        
    [Point 7]     [CENTER]       [Point 3]
    
           [Point 6]              [Point 4]
                    [Point 5]
```

**Interactive Behavior**:
- On hover over a point: popover appears near the point
- Popover shows icon + title + benefit description
- Center circle pulses gently
- Points have subtle hover scale effect

**Deliverables**:
- `features-solar-system.tsx` component
- Orbital animation system
- Interactive hover popovers
- Non-technical copy for all feature points

---

## Phase 3: Process Timeline & Value Display


### 3.2 Everything Included - Technical Language Cleanup ✅ COMPLETED
**File**: Modify `apps/web/src/app/landing/page.tsx` (What You Get section)

**Status**: All changes implemented and verified

**Completed Items** (benefit-focused language):
- ✓ "Professional custom design built for your brand"
- ✓ "Works perfectly on phones and tablets"
- ✓ "Loads instantly so customers don't wait"
- ✓ "Found easily on Google search"
- ✓ "Secure and trusted by visitors"
- ✓ "Connect with your customers easily"
- ✓ "Share your success on social media"
- ✓ "Fast, reliable hosting included for a year"
- ✓ "We watch your site's health for you"
- ✓ "Free small changes for 30 days after launch"

**Deliverables**:
- ✓ Simplified, benefit-focused language
- ✓ Same features, clearer communication
- ✓ Production build successful

---

## Phase 4: Enhanced Pricing Structure

### 4.1 Pricing Redesign - Fix Size & Language
**File**: `apps/web/src/components/landing/pricing-configurator.tsx` + `apps/web/src/lib/pricing.ts`

**CRITICAL ISSUES IN CURRENT IMPLEMENTATION**:
1. **Size**: Professional Website card is NOT the same size as others (must be equal)
2. **Hosting**: Professional Website mentions hosting (REMOVE - hosting is separate service)
3. **Language**: Text is too technical (simplify per documentation)

**New Pricing Structure**:

#### Main Package:
1. **Professional Website** - $1,000 (one-time)
   - Landing page
   - Beautiful design that matches your brand
   - Works perfectly on phones and tablets
   - Easy way for customers to contact you

   this one card is bigger and align with the pricing on the right; the pricings below should be below the Professional Website and the pricing in a dropdown, the dropdown like faq should say: extra services

#### Extra Services (Dropdown/Collapsible Section):
- **Additional Pages** - $150 per page (one-time, up to 50 pages)
  - Add more pages to your site
  - Same beautiful design quality

- **Advanced Features** - $300-$1,000 (one-time)
  - Connect to special tools
  - Custom functionality for your business
  - API integrations

- **Maintenance Service** - $500/month
  - 1-hour strategy meeting every month
  - 3 updates or changes per month
  - We watch your site's performance
  - Keep everything secure

- **Hosting Service** - $200/month (SEPARATE FROM PROFESSIONAL WEBSITE)
  - Fast, reliable website hosting
  - Automatic scaling
  - Secure SSL certificate
  - Automatic backups

**Design Requirements**:
- All 3 main cards MUST be equal height and width
- Professional Website should be highlighted (slight glow)
- Professional Website should NOT mention hosting
- Use simple, benefit-focused language (NOT technical)
- Clear "ONE-TIME" vs "MONTHLY" badges
- Extra services in expandable section below

**Deliverables**:
- Equal-sized pricing cards
- Remove hosting from Professional package features
- Simplified, non-technical language throughout
- Hosting as separate monthly service only

---

### 4.2 Pricing Table Display
**File**: `apps/web/src/lib/pricing.ts` (update)

**Data Structure**:
```typescript
interface PricingOption {
  id: string
  name: string
  price: number
  billingCycle: 'one-time' | 'monthly'
  description: string
  features: Feature[]
  highlight?: boolean
  category: 'main' | 'addon' | 'service'
}

interface Feature {
  text: string
  limit?: number | 'unlimited'
  description?: string
}
```

**Deliverables**:
- Updated pricing data structure
- Proper categorization and metadata
- New services and pricing tiers

---

## Phase 5: Footer & UI Cleanup

### 5.1 Remove Bottom Yellow CTA Bar
**File**: `apps/web/src/app/page.tsx`

**Requirements**:
- **REMOVE**: StickyCTABar component completely
- This is the ugly yellow sticky bar at the bottom
- Remove import and component usage
- Keep RiskReversalBadge (green badge on right side)

**Deliverables**:
- No yellow sticky CTA bar at bottom
- Cleaner page layout

---


### 5.2 Testimonials Wall - Complete Redesign
**File**: `apps/web/src/components/landing/social-wall.tsx`

**Current State**: Single horizontal scrolling row with 12 customers

**CRITICAL ISSUES TO FIX**:
1. **Bug**: Current implementation has bugs in the carousel
2. **Images**: Need client photos downloaded from internet (not SVG avatars - download human pictures from the internet and use them, random people)
3. **Layout**: Should be 3 SEPARATE rows of carousels
4. **Size**: Make cards SMALLER in height
5. **Width**: Full component/container width - 100%
6. **Direction**: Some rows scroll left, some scroll right (alternating)
7. on mouse hover, the carrossels stop and the testimonial that he hover zooms in and the others blur

**New Requirements**:

**3-Row Carousel System**:
- Row 1: Scrolls LEFT → RIGHT (customers 1-8)
- Row 2: Scrolls RIGHT → LEFT (customers 9-16)  
- Row 3: Scrolls LEFT → RIGHT (customers 17-24)

**Card Design**:
- Height: Reduce by 30-40% (make smaller/more compact)
- Width: Full page width with no container limits
- Remove gradient edge overlays (full width carousel)
- Cards should be smaller overall

**Client Images**:
- Download 24 REAL person photos from internet
- Use headshots
- Match gender to names (Sarah = female, Marcus = male, etc.)
- Store in `public/clients/` directory
- Format: JPG or PNG, optimized for web

**Carousel Behavior**:
- Continuous auto-scroll (no stop on hover)
- Smooth infinite loop
- Different speeds for visual interest
- No pause functionality

**Deliverables**:
- 3 separate horizontal carousels
- Real client photos (12 images downloaded)
- Smaller card height
- Full-width layout
- Alternating scroll directions
- Fixed bugs in current implementation

---
