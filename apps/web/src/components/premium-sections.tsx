/**
 * Premium Section Components Library
 * 
 * Maps componentId to React components that render high-end, branded layouts.
 * Each component receives section data and design DNA (colors, typography, styling).
 */

import React from 'react';
import type { SiteSection } from '@/lib/types';

export interface ComponentProps {
  section: SiteSection;
  index: number;
  mode: 'light' | 'dark' | 'colorful';
  dna: {
    maskImage: string;
    borderRadius: string;
    fontFamily: string;
    accentHue: string;
    hash: number;
  };
  contentTone: string;
  bodyTone: string;
  sectionTone: string;
  panelTone: string;
  polish: (text: string) => string;
}

/**
 * HeroSplitEditorial: Large hero with editorial image treatment
 * Hero image on right, headline + subheading + dual CTA on left
 */
export const HeroSplitEditorial: React.FC<ComponentProps> = ({
  section,
  mode,
  dna,
  contentTone,
  bodyTone,
  polish,
}) => (
  <header className="relative py-16 md:py-32 flex flex-col justify-center min-h-[60vh]">
    <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
      <div>
        <h1
          style={{ fontFamily: dna.fontFamily }}
          className="text-5xl md:text-7xl font-bold leading-[1.05] tracking-tight drop-shadow-sm"
        >
          {polish(section.headline)}
        </h1>
        <p className={`mt-8 text-xl leading-relaxed ${bodyTone}`}>
          {polish(section.body || section.supportingLine || '')}
        </p>
      </div>
      <div
        className="h-96 md:h-[600px] opacity-80 blur-sm rounded-2xl"
        style={{
          backgroundColor: dna.accentHue,
          opacity: 0.15,
        }}
      />
    </div>
  </header>
);

/**
 * HeroCentered: Centered hero with headline, subheading, and primary CTA
 */
export const HeroCentered: React.FC<ComponentProps> = ({
  section,
  mode,
  dna,
  contentTone,
  bodyTone,
  polish,
}) => (
  <header className="relative py-24 md:py-40 flex flex-col items-center justify-center text-center">
    <h1
      style={{ fontFamily: dna.fontFamily }}
      className="max-w-4xl text-5xl md:text-7xl font-bold leading-[1.05] tracking-tight"
    >
      {polish(section.headline)}
    </h1>
    <p className={`mt-10 max-w-2xl text-xl md:text-2xl leading-relaxed ${bodyTone}`}>
      {polish(section.body || section.supportingLine || '')}
    </p>
  </header>
);

/**
 * ServicesBento: 2x3 grid bento layout for services/features
 * First item spans 2 rows, others in grid
 */
export const ServicesBento: React.FC<ComponentProps> = ({
  section,
  dna,
  contentTone,
  bodyTone,
  panelTone,
  polish,
}) => {
  const items = section.items.filter(Boolean);
  return (
    <section className={`border-t ${panelTone} py-16 md:py-28`}>
      <div className="mb-10 flex flex-col gap-4">
        <div className="text-xs font-semibold uppercase tracking-[0.24em]" style={{ color: dna.accentHue }}>
          {section.title || 'Services'}
        </div>
        <h2 className={`text-4xl md:text-6xl font-semibold tracking-tight ${contentTone}`} style={{ fontFamily: dna.fontFamily }}>
          {polish(section.headline)}
        </h2>
      </div>
      <div className="grid gap-4 md:grid-cols-3 auto-rows-[300px]">
        {items.map((item, idx) => (
          <div
            key={idx}
            className={`border p-6 ${panelTone} ${dna.borderRadius} flex flex-col justify-between ${idx === 0 ? 'md:row-span-2' : ''}`}
          >
            <div>
              <div className="mb-4 h-1 w-10 rounded-full" style={{ backgroundColor: dna.accentHue }} />
              <div className={`text-lg md:text-xl font-semibold leading-tight ${contentTone}`}>
                {polish(item)}
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
};

/**
 * ProofCarousel: Testimonials/proof points in rotating carousel layout
 * Grid of proof cards with author/title and quote
 */
export const ProofCarousel: React.FC<ComponentProps> = ({
  section,
  dna,
  contentTone,
  bodyTone,
  panelTone,
  polish,
}) => {
  const items = section.items.filter(Boolean);
  return (
    <section className={`border-t ${panelTone} py-16 md:py-28`}>
      <div className="mb-12 flex flex-col gap-4">
        <div className="text-xs font-semibold uppercase tracking-[0.24em]" style={{ color: dna.accentHue }}>
          {section.title || 'Testimonials'}
        </div>
        <h2 className={`text-4xl md:text-6xl font-semibold tracking-tight ${contentTone}`} style={{ fontFamily: dna.fontFamily }}>
          {polish(section.headline)}
        </h2>
      </div>
      <div className="grid gap-6 md:grid-cols-2">
        {items.slice(0, 4).map((item, idx) => {
          const match = polish(item).match(/^([^:]+):(.*)$/);
          const isQuote = item.includes('"');
          return (
            <div key={idx} className={`border p-8 ${panelTone} ${dna.borderRadius}`}>
              {match ? (
                <>
                  <p className={`mb-4 text-lg leading-relaxed italic ${bodyTone}`}>"{match[2].trim()}"</p>
                  <p className={`text-sm font-semibold ${contentTone}`}>{match[1]}</p>
                </>
              ) : (
                <p className={`text-lg leading-relaxed ${isQuote ? 'italic' : ''} ${contentTone}`}>
                  "{polish(item)}"
                </p>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
};

/**
 * TimelineVertical: Vertical timeline of steps, process, or journey
 * Left label, right content with connecting line
 */
export const TimelineVertical: React.FC<ComponentProps> = ({
  section,
  dna,
  contentTone,
  bodyTone,
  panelTone,
  polish,
}) => {
  const items = section.items.filter(Boolean);
  return (
    <section className={`border-t ${panelTone} py-16 md:py-28`}>
      <div className="mb-12 grid gap-10 md:grid-cols-[0.85fr_1.15fr]">
        <div>
          <div className="text-xs font-semibold uppercase tracking-[0.24em]" style={{ color: dna.accentHue }}>
            {section.title || 'Timeline'}
          </div>
          <h2 className={`mt-4 text-4xl md:text-6xl font-semibold tracking-tight ${contentTone}`} style={{ fontFamily: dna.fontFamily }}>
            {polish(section.headline)}
          </h2>
        </div>
      </div>
      <div className="space-y-6 md:ml-20">
        {items.map((item, idx) => (
          <div key={idx} className="relative">
            <div className="absolute left-0 top-0 h-full w-px -translate-x-5" style={{ backgroundColor: dna.accentHue, opacity: 0.3 }} />
            <div className="absolute left-0 top-2 -translate-x-[11px] w-4 h-4 rounded-full border-2" style={{ borderColor: dna.accentHue, backgroundColor: 'transparent' }} />
            <div className={`border p-6 ${panelTone} ${dna.borderRadius} ml-8`}>
              <span className="font-mono text-sm font-semibold" style={{ color: dna.accentHue }}>
                Step {idx + 1}
              </span>
              <p className={`mt-3 text-lg leading-relaxed ${contentTone}`}>{polish(item)}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
};

/**
 * GalleryMasonry: Masonry gallery grid (3-column with varied sizes)
 */
export const GalleryMasonry: React.FC<ComponentProps> = ({
  section,
  dna,
  contentTone,
  bodyTone,
  panelTone,
  polish,
}) => {
  const items = section.items.filter(Boolean);
  return (
    <section className={`border-t ${panelTone} py-16 md:py-28`}>
      <div className="mb-12 flex flex-col gap-4">
        <div className="text-xs font-semibold uppercase tracking-[0.24em]" style={{ color: dna.accentHue }}>
          {section.title || 'Gallery'}
        </div>
        <h2 className={`text-4xl md:text-6xl font-semibold tracking-tight ${contentTone}`} style={{ fontFamily: dna.fontFamily }}>
          {polish(section.headline)}
        </h2>
      </div>
      <div className="grid gap-4 md:grid-cols-3 auto-rows-[250px]">
        {items.map((item, idx) => (
          <div
            key={idx}
            className={`group overflow-hidden border p-6 ${panelTone} ${dna.borderRadius} flex flex-col justify-between ${idx % 3 === 0 ? 'md:row-span-2' : ''}`}
          >
            <div className="mb-8 h-20 rounded-full opacity-20 blur-2xl transition-transform group-hover:scale-125" style={{ backgroundColor: dna.accentHue }} />
            <div className={`text-lg font-semibold leading-tight ${contentTone}`}>{polish(item)}</div>
          </div>
        ))}
      </div>
    </section>
  );
};

/**
 * EditorialFeature: Large featured section with image, headline, body, and bullet points
 * Full-width immersive layout
 */
export const EditorialFeature: React.FC<ComponentProps> = ({
  section,
  dna,
  contentTone,
  bodyTone,
  panelTone,
  polish,
}) => {
  const items = section.items.filter(Boolean);
  return (
    <section className={`border-t ${panelTone} py-16 md:py-28`}>
      <div className={`border px-8 py-12 md:px-16 md:py-20 ${panelTone} ${dna.borderRadius}`}>
        <div className="grid gap-12 md:grid-cols-2 md:items-start">
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.24em]" style={{ color: dna.accentHue }}>
              {section.title || 'Feature'}
            </div>
            <h2 className={`mt-6 text-4xl md:text-5xl font-semibold tracking-tight ${contentTone}`} style={{ fontFamily: dna.fontFamily }}>
              {polish(section.headline)}
            </h2>
          </div>
          <div>
            <p className={`text-lg md:text-xl leading-relaxed ${bodyTone}`}>
              {polish(section.body || '')}
            </p>
            {items.length > 0 && (
              <ul className="mt-8 space-y-3">
                {items.slice(0, 4).map((item, idx) => (
                  <li key={idx} className={`flex gap-3 text-base ${contentTone}`}>
                    <span style={{ color: dna.accentHue }}>✓</span>
                    <span>{polish(item)}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
    </section>
  );
};

/**
 * CtaBanner: High-impact CTA section with headline and action
 */
export const CtaBanner: React.FC<ComponentProps> = ({
  section,
  dna,
  contentTone,
  panelTone,
  polish,
}) => (
  <section className={`border-t ${panelTone} py-16 md:py-24`}>
    <div className={`relative overflow-hidden border p-12 md:p-20 ${panelTone} ${dna.borderRadius}`}>
      <div className="absolute -right-24 -top-24 h-64 w-64 rounded-full opacity-20 blur-3xl" style={{ backgroundColor: dna.accentHue }} />
      <div className="relative text-center">
        <h2 className={`text-4xl md:text-5xl font-semibold tracking-tight ${contentTone}`} style={{ fontFamily: dna.fontFamily }}>
          {polish(section.headline)}
        </h2>
        {section.body && (
          <p className={`mt-6 text-lg leading-relaxed ${contentTone} opacity-80`}>
            {polish(section.body)}
          </p>
        )}
      </div>
    </div>
  </section>
);

/**
 * StickyCta: Sticky footer CTA that appears during scroll
 */
export const StickyCta: React.FC<ComponentProps> = ({
  section,
  dna,
  contentTone,
  panelTone,
  polish,
}) => (
  <section className={`fixed bottom-0 left-0 right-0 border-t ${panelTone} py-4 md:py-6 px-4`} style={{ zIndex: 30, backdropFilter: 'blur(12px)' }}>
    <div className="mx-auto max-w-7xl flex items-center justify-between">
      <div>
        <h3 className={`text-lg md:text-xl font-semibold ${contentTone}`}>
          {polish(section.headline)}
        </h3>
      </div>
      <button
        className="rounded-full px-8 py-2.5 text-base font-semibold text-white hover:opacity-90 transition-opacity"
        style={{ backgroundColor: dna.accentHue }}
      >
        {polish(section.ctaLabel || 'Get started')}
      </button>
    </div>
  </section>
);

/**
 * Component registry mapping componentId to React component
 */
export const PREMIUM_COMPONENTS: Record<string, React.FC<ComponentProps>> = {
  'hero-split-editorial': HeroSplitEditorial,
  'hero-centered': HeroCentered,
  'services-bento': ServicesBento,
  'proof-carousel': ProofCarousel,
  'timeline-vertical': TimelineVertical,
  'gallery-masonry': GalleryMasonry,
  'editorial-feature': EditorialFeature,
  'cta-banner': CtaBanner,
  'cta-sticky': StickyCta,
};

export function getPremiumComponent(componentId?: string): React.FC<ComponentProps> | null {
  if (!componentId) return null;
  return PREMIUM_COMPONENTS[componentId] || null;
}
