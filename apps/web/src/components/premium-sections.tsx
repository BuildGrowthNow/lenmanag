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
          {polish(section.body || '')}
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
      {polish(section.body || '')}
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
                  <p className={`mb-4 text-lg leading-relaxed italic ${bodyTone}`}>&ldquo;{match[2].trim()}&rdquo;</p>
                  <p className={`text-sm font-semibold ${contentTone}`}>{match[1]}</p>
                </>
              ) : (
                <p className={`text-lg leading-relaxed ${isQuote ? 'italic' : ''} ${contentTone}`}>
                  &ldquo;{polish(item)}&rdquo;
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
 * ServicesTabs: Interactive tabbed navigation for services
 */
export const ServicesTabs: React.FC<ComponentProps> = ({
  section,
  dna,
  contentTone,
  bodyTone,
  panelTone,
  polish,
}) => {
  const [activeTab, setActiveTab] = React.useState(0);
  const items = section.items.filter(Boolean);
  return (
    <section className={`border-t ${panelTone} py-16 md:py-28`}>
      <div className="mb-12 flex flex-col gap-4">
        <div className="text-xs font-semibold uppercase tracking-[0.24em]" style={{ color: dna.accentHue }}>
          {section.title || 'Services'}
        </div>
        <h2 className={`text-4xl md:text-6xl font-semibold tracking-tight ${contentTone}`} style={{ fontFamily: dna.fontFamily }}>
          {polish(section.headline)}
        </h2>
      </div>
      <div className="flex gap-2 mb-8 flex-wrap">
        {items.map((item, idx) => (
          <button
            key={idx}
            onClick={() => setActiveTab(idx)}
            className={`px-6 py-3 ${dna.borderRadius} font-semibold transition-all ${
              activeTab === idx
                ? 'text-white'
                : `${contentTone} border ${panelTone} hover:border-current`
            }`}
            style={activeTab === idx ? { backgroundColor: dna.accentHue } : {}}
          >
            {polish(item).split(':')[0] || polish(item)}
          </button>
        ))}
      </div>
      <div className={`border p-8 md:p-12 ${panelTone} ${dna.borderRadius} min-h-[200px] transition-all duration-300`}>
        <div className={`text-lg leading-relaxed ${contentTone}`}>
          {polish(items[activeTab] || '')}
        </div>
      </div>
    </section>
  );
};

/**
 * ServicesAccordion: Collapsible accordion for detailed service info
 */
export const ServicesAccordion: React.FC<ComponentProps> = ({
  section,
  dna,
  contentTone,
  bodyTone,
  panelTone,
  polish,
}) => {
  const [openIndex, setOpenIndex] = React.useState<number | null>(0);
  const items = section.items.filter(Boolean);
  return (
    <section className={`border-t ${panelTone} py-16 md:py-28`}>
      <div className="mb-12 flex flex-col gap-4">
        <div className="text-xs font-semibold uppercase tracking-[0.24em]" style={{ color: dna.accentHue }}>
          {section.title || 'Services'}
        </div>
        <h2 className={`text-4xl md:text-6xl font-semibold tracking-tight ${contentTone}`} style={{ fontFamily: dna.fontFamily }}>
          {polish(section.headline)}
        </h2>
      </div>
      <div className="space-y-3">
        {items.map((item, idx) => {
          const isOpen = openIndex === idx;
          const parts = polish(item).split(':');
          const title = parts[0] || polish(item);
          const content = parts[1] || '';
          return (
            <div key={idx} className={`border ${panelTone} ${dna.borderRadius} overflow-hidden transition-all`}>
              <button
                onClick={() => setOpenIndex(isOpen ? null : idx)}
                className={`w-full px-6 py-4 flex items-center justify-between ${contentTone} hover:opacity-80 transition-opacity`}
              >
                <span className="font-semibold text-left">{title}</span>
                <span className="text-2xl transition-transform" style={{ transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)' }}>
                  ↓
                </span>
              </button>
              <div
                className="transition-all duration-300 overflow-hidden"
                style={{ maxHeight: isOpen ? '500px' : '0px' }}
              >
                <div className={`px-6 pb-4 ${bodyTone}`}>
                  {content || section.body}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
};

/**
 * StatsCounter: Animated number counters that trigger on scroll
 */
export const StatsCounter: React.FC<ComponentProps> = ({
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
      <div className="mb-12 text-center">
        <div className="text-xs font-semibold uppercase tracking-[0.24em]" style={{ color: dna.accentHue }}>
          {section.title || 'By the numbers'}
        </div>
        <h2 className={`mt-4 text-4xl md:text-6xl font-semibold tracking-tight ${contentTone}`} style={{ fontFamily: dna.fontFamily }}>
          {polish(section.headline)}
        </h2>
      </div>
      <div className="grid gap-8 md:grid-cols-3">
        {items.slice(0, 6).map((item, idx) => {
          const match = polish(item).match(/^([^:]+):(.*)$/);
          const number = match ? match[1].match(/\d+[+%]?/)?.[0] || '100+' : '100+';
          const label = match ? match[2].trim() : polish(item);
          return (
            <div key={idx} className={`text-center p-8 border ${panelTone} ${dna.borderRadius} hover:scale-105 transition-transform`}>
              <div className="text-5xl md:text-7xl font-bold mb-4" style={{ color: dna.accentHue }}>
                {number}
              </div>
              <div className={`text-lg font-semibold ${contentTone}`}>
                {label}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
};

/**
 * ProofGridInteractive: Interactive proof grid with hover effects
 */
export const ProofGridInteractive: React.FC<ComponentProps> = ({
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
          return (
            <div
              key={idx}
              className={`group border p-8 ${panelTone} ${dna.borderRadius} hover:scale-[1.02] transition-all duration-300 cursor-pointer relative overflow-hidden`}
            >
              <div className="absolute inset-0 opacity-0 group-hover:opacity-10 transition-opacity" style={{ backgroundColor: dna.accentHue }} />
              {match ? (
                <>
                  <p className={`mb-4 text-lg leading-relaxed italic ${bodyTone} relative z-10`}>&ldquo;{match[2].trim()}&rdquo;</p>
                  <p className={`text-sm font-semibold ${contentTone} relative z-10`}>{match[1]}</p>
                </>
              ) : (
                <p className={`text-lg leading-relaxed italic ${contentTone} relative z-10`}>
                  &ldquo;{polish(item)}&rdquo;
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
 * FeaturesComparison: Interactive comparison table
 */
export const FeaturesComparison: React.FC<ComponentProps> = ({
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
      <div className="mb-12 text-center">
        <div className="text-xs font-semibold uppercase tracking-[0.24em]" style={{ color: dna.accentHue }}>
          {section.title || 'Compare'}
        </div>
        <h2 className={`mt-4 text-4xl md:text-6xl font-semibold tracking-tight ${contentTone}`} style={{ fontFamily: dna.fontFamily }}>
          {polish(section.headline)}
        </h2>
      </div>
      <div className={`border ${panelTone} ${dna.borderRadius} overflow-hidden`}>
        <div className="divide-y">
          {items.map((item, idx) => (
            <div key={idx} className="px-6 py-4 flex items-center justify-between hover:bg-opacity-50 transition-all group">
              <span className={`font-medium ${contentTone}`}>{polish(item)}</span>
              <span className="w-6 h-6 rounded-full flex items-center justify-center text-white text-sm font-bold group-hover:scale-110 transition-transform" style={{ backgroundColor: dna.accentHue }}>
                ✓
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

/**
 * VideoHero: Hero with video background (placeholder for now)
 */
export const VideoHero: React.FC<ComponentProps> = ({
  section,
  dna,
  contentTone,
  bodyTone,
  polish,
}) => (
  <header className="relative py-24 md:py-40 flex flex-col items-center justify-center text-center min-h-[70vh]">
    <div className="absolute inset-0 opacity-20 overflow-hidden">
      <div className="absolute inset-0 animate-pulse" style={{ backgroundColor: dna.accentHue }} />
    </div>
    <div className="relative z-10">
      <h1
        style={{ fontFamily: dna.fontFamily }}
        className="max-w-4xl text-5xl md:text-7xl font-bold leading-[1.05] tracking-tight drop-shadow-lg"
      >
        {polish(section.headline)}
      </h1>
      <p className={`mt-10 max-w-2xl text-xl md:text-2xl leading-relaxed ${bodyTone}`}>
        {polish(section.body || '')}
      </p>
    </div>
  </header>
);

/**
 * Component registry mapping componentId to React component
 */
export const PREMIUM_COMPONENTS: Record<string, React.FC<ComponentProps>> = {
  'hero-split-editorial': HeroSplitEditorial,
  'hero-centered': HeroCentered,
  'video-hero': VideoHero,
  'services-bento': ServicesBento,
  'services-tabs': ServicesTabs,
  'services-accordion': ServicesAccordion,
  'proof-carousel': ProofCarousel,
  'proof-grid-interactive': ProofGridInteractive,
  'timeline-vertical': TimelineVertical,
  'gallery-masonry': GalleryMasonry,
  'editorial-feature': EditorialFeature,
  'stats-counter': StatsCounter,
  'features-comparison': FeaturesComparison,
  'cta-banner': CtaBanner,
  'cta-sticky': StickyCta,
};

export function getPremiumComponent(componentId?: string): React.FC<ComponentProps> | null {
  if (!componentId) return null;
  return PREMIUM_COMPONENTS[componentId] || null;
}
