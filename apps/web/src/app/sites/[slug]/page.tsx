"use client";

import { use, useEffect, useRef, useState } from "react";
import Link from "next/link";
import Image from "next/image";

import { EmptyState } from "@/components/state/empty-state";
import { Button } from "@/components/ui/button";
import { getPublicSite, normalizePreviewSlug } from "@/lib/api/sites";
import { sendAnalyticsEvent } from "@/lib/analytics";
import type { AnalyticsEventType, GeneratedSite, SiteSection, BriefSourceReference } from "@/lib/types";
import { getPremiumComponent } from "@/components/premium-sections";
import type { ComponentProps } from "@/components/premium-sections";

function paletteBackground(mode: string) {
  if (mode === "colorful") return "radial-gradient(circle at top, rgba(249,115,22,0.12), transparent 30%), linear-gradient(180deg, rgba(8,17,31,0) 0%, #040814 100%)";
  if (mode === "light") return "radial-gradient(circle at top, rgba(59,130,246,0.08), transparent 28%), linear-gradient(180deg, rgba(248,250,252,0) 0%, #e2e8f0 100%)";
  return "radial-gradient(circle at top, rgba(148,163,184,0.06), transparent 28%), linear-gradient(180deg, rgba(11,15,20,0) 0%, #05070a 100%)";
}

function deriveDesignDNA(site: GeneratedSite) {
  const seed = String(site.layoutHash || site.previewSlug || "default");
  let hash = 0;
  for (let i = 0; i < seed.length; i++) {
    hash = seed.charCodeAt(i) + ((hash << 5) - hash);
  }
  hash = Math.abs(hash);

  const masks = [
    "radial-gradient(70% 70% at 70% 50%, black 40%, transparent 100%)",
    "linear-gradient(270deg, black 30%, transparent 100%)",
    "radial-gradient(ellipse at 80% 50%, black 45%, transparent 100%)"
  ];

  const radii = ["rounded-none", "rounded-md", "rounded-xl", "rounded-[2rem]"];
  const typographyVal = (site.brandTokens.typography?.value || "").toLowerCase();
  const fontFamily = typographyVal.includes("serif") ? "var(--font-heading)" : typographyVal.includes("mono") ? "var(--font-mono)" : "inherit";

  const accents = [
    site.brandTokens.accentColor?.value,
    site.brandTokens.primaryColor?.value,
    site.paletteMode === "colorful" ? "#f97316" : "#3b82f6"
  ].filter(Boolean);

  return {
    maskImage: masks[hash % masks.length],
    borderRadius: radii[hash % radii.length],
    fontFamily,
    accentHue: accents[0] || "#3b82f6",
    hash
  };
}

function sectionTone(index: number, mode: string) {
  if (mode === "light") return index === 0 ? "border-transparent" : "border-slate-300/50";
  return index === 0 ? "border-transparent" : "border-white/10";
}

function contentTone(mode: string) {
  return mode === "light" ? "text-slate-900" : "text-slate-50";
}

function mutedTone(mode: string) {
  return mode === "light" ? "text-slate-600" : "text-slate-400";
}

const FORBIDDEN_TERMS = [
  "source-safe",
  "source traceability",
  "generation",
  "generated",
  "quality score",
  "qa status",
  "readiness",
  "job id",
  "operator",
  "admin",
  "evidence",
  "inference",
  "extracted cues",
  "extracted logo",
  "extracted color",
  "extracted typography",
  "brand cues",
  "conversion path",
  "cta pattern",
  "source cues",
  "crawl",
  "extraction",
  "brief",
  "missing requirements",
  "preview runtime",
];

function stripInstructionLeads(text: string): string {
  const value = String(text || "").trim();
  if (!value) return value;
  let out = value.replace(/^(use|leverage|make|choose|write)\b[^:]{0,120}:\s*/i, "");
  out = out.replace(/\b(homepage\s+title|meta\s+description|primary\s+heading|h1)\s*:\s*/gi, "");
  for (const sep of ["|", "—", "-", "\n"]) {
    if (out.includes(sep)) {
      const parts = out.split(sep).map((p) => p.trim()).filter(Boolean);
      if (parts.length) {
        out = parts[0];
        break;
      }
    }
  }
  return out;
}

function sanitizePublicText(text: string): string {
  let out = String(text || "");
  for (const term of FORBIDDEN_TERMS) {
    const re = new RegExp(term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "gi");
    out = out.replace(re, "");
  }
  out = out.replace(/\s{2,}/g, " ").trim();
  out = out.replace(/\s+[.:;,-]$/g, "");
  return out;
}

function polish(text: string): string {
  return sanitizePublicText(stripInstructionLeads(text));
}

function ensureClientCta(label: string): string {
  const t = String(label || "");
  if (/preview/i.test(t)) return "Learn more";
  return t;
}

function imageFromReferences(refs: BriefSourceReference[] | undefined): string | null {
  if (!refs || !refs.length) return null;
  for (const ref of refs) {
    if (ref.kind === "asset" && (ref.assetType === "image" || ref.assetType === "logo")) {
      // Prefer the excerpt if it looks like an actual image URL; fall back to sourceUrl.
      if (ref.excerpt && /^https?:\/\//i.test(ref.excerpt)) return ref.excerpt;
      if (/^https?:\/\//i.test(ref.sourceUrl)) return ref.sourceUrl;
    }
  }
  return null;
}

function heroImage(site: GeneratedSite | null | undefined): string | null {
  if (!site) return null;
  const tokens = site.brandTokens;
  const fromLogo = imageFromReferences((tokens as any)?.logoAsset?.evidence?.references);
  if (fromLogo) return fromLogo;
  const fromImage = imageFromReferences(tokens.imageStyle?.evidence?.references);
  if (fromImage) return fromImage;
  if (site.screenshotRefs && site.screenshotRefs.length > 0) {
    return site.screenshotRefs[0].url;
  }
  return null;
}

function renderSection(section: SiteSection, index: number, mode: string, dna: ReturnType<typeof deriveDesignDNA>) {
  const contentToneCls = contentTone(mode);
  const bodyToneCls = mutedTone(mode);
  const panelToneCls = mode === "light" ? "bg-white/70 border-slate-200 shadow-[0_24px_80px_rgba(15,23,42,0.08)]" : "bg-white/[0.045] border-white/10 shadow-[0_24px_90px_rgba(0,0,0,0.28)]";
  const sectionToneCls = sectionTone(index, mode);

  // Try premium component first if componentId is present
  if (section.componentId) {
    const PremiumComponent = getPremiumComponent(section.componentId);
    if (PremiumComponent) {
      const props: ComponentProps = {
        section,
        index,
        mode: mode as 'light' | 'dark' | 'colorful',
        dna,
        contentTone: contentToneCls,
        bodyTone: bodyToneCls,
        sectionTone: sectionToneCls,
        panelTone: panelToneCls,
        polish,
      };
      return (
        <div key={`premium-${section.componentId}-${index}`}>
          <PremiumComponent {...props} />
        </div>
      );
    }
  }

  // Fallback to existing logic for non-premium sections
  const kind = `${section.kind} ${section.title}`.toLowerCase();
  const isServices = /service|offering/i.test(kind);
  const isProof = /proof|highlight|testimonial|result|trust/i.test(kind);
  const isProcess = /process|method|approach/i.test(kind);
  const isPricing = /pricing|package|plan/i.test(kind);
  const isGallery = /gallery|portfolio|work/i.test(kind);
  const isAbout = /about|point of view|story/i.test(kind);
  const isContact = /contact|book|schedule|quote/i.test(kind);

  const items = section.items.filter((v) => !FORBIDDEN_TERMS.some((t) => (v || "").toLowerCase().includes(t)));
  const titleTone = contentToneCls;
  const bodyTone = bodyToneCls;
  const panelTone = panelToneCls;

  if (isGallery) {
    return (
      <section id={`section-${index}`} className={`border-t ${sectionTone(index, mode)} py-16 md:py-28`} style={{ animation: "fadeIn 0.8s ease-out backwards" }}>
        <div className="mb-10 flex flex-col gap-4 md:max-w-3xl">
          <div className="text-xs font-semibold uppercase tracking-[0.24em]" style={{ color: dna.accentHue }}>Selected work</div>
          <h2 className={`text-4xl md:text-6xl font-semibold tracking-tight ${titleTone}`} style={{ fontFamily: dna.fontFamily }}>{polish(section.headline)}</h2>
          {section.body ? <p className={`text-lg leading-relaxed ${bodyTone}`}>{polish(section.body)}</p> : null}
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {(items.length ? items : [section.body, section.headline]).slice(0, 6).map((item, itemIndex) => (
            <div key={itemIndex} className={`group min-h-56 overflow-hidden border p-6 ${panelTone} ${itemIndex % 3 === 0 ? "md:row-span-2" : ""} ${dna.borderRadius}`}>
              <div className="mb-10 h-24 rounded-full opacity-25 blur-2xl transition-transform group-hover:scale-125" style={{ backgroundColor: dna.accentHue }} />
              <div className={`text-xl font-semibold leading-tight ${titleTone}`}>{polish(item || section.headline)}</div>
            </div>
          ))}
        </div>
      </section>
    );
  }

  if (isProcess) {
    return (
      <section id={`section-${index}`} className={`border-t ${sectionTone(index, mode)} py-16 md:py-28`} style={{ animation: "fadeIn 0.8s ease-out backwards" }}>
        <div className="grid gap-10 md:grid-cols-[0.85fr_1.15fr] md:items-start">
          <div className="md:sticky md:top-24">
            <div className="text-xs font-semibold uppercase tracking-[0.24em]" style={{ color: dna.accentHue }}>Method</div>
            <h2 className={`mt-4 text-4xl md:text-6xl font-semibold tracking-tight ${titleTone}`} style={{ fontFamily: dna.fontFamily }}>{polish(section.headline)}</h2>
            {section.body ? <p className={`mt-6 text-lg leading-relaxed ${bodyTone}`}>{polish(section.body)}</p> : null}
          </div>
          <div className="space-y-4">
            {(items.length ? items : [section.body]).slice(0, 5).map((item, itemIndex) => (
              <div key={itemIndex} className={`border p-6 ${panelTone} ${dna.borderRadius}`}>
                <div className="mb-6 flex items-center gap-4">
                  <span className="font-mono text-sm" style={{ color: dna.accentHue }}>{String(itemIndex + 1).padStart(2, "0")}</span>
                  <div className="h-px flex-1 opacity-40" style={{ backgroundColor: dna.accentHue }} />
                </div>
                <div className={`text-xl leading-relaxed ${titleTone}`}>{polish(item || "A clearer next step")}</div>
              </div>
            ))}
          </div>
        </div>
      </section>
    );
  }

  if (isAbout) {
    return (
      <section id={`section-${index}`} className={`border-t ${sectionTone(index, mode)} py-16 md:py-28`} style={{ animation: "fadeIn 0.8s ease-out backwards" }}>
        <div className={`border px-6 py-10 md:px-12 md:py-14 ${panelTone} ${dna.borderRadius}`}>
          <div className="grid gap-10 md:grid-cols-12 md:items-end">
            <div className="md:col-span-5 text-xs font-semibold uppercase tracking-[0.24em]" style={{ color: dna.accentHue }}>Point of view</div>
            <div className="md:col-span-7">
              <h2 className={`text-4xl md:text-6xl font-semibold tracking-tight ${titleTone}`} style={{ fontFamily: dna.fontFamily }}>{polish(section.headline)}</h2>
              {section.body ? <p className={`mt-8 text-xl md:text-2xl leading-relaxed ${bodyTone}`}>{polish(section.body)}</p> : null}
            </div>
          </div>
        </div>
      </section>
    );
  }

  if (isPricing || isContact) {
    return (
      <section id={`section-${index}`} className={`border-t ${sectionTone(index, mode)} py-16 md:py-28`} style={{ animation: "fadeIn 0.8s ease-out backwards" }}>
        <div className={`relative overflow-hidden border p-8 md:p-12 ${panelTone} ${dna.borderRadius}`}>
          <div className="absolute -right-24 -top-24 h-64 w-64 rounded-full opacity-20 blur-3xl" style={{ backgroundColor: dna.accentHue }} />
          <div className="relative grid gap-10 md:grid-cols-[1.1fr_0.9fr] md:items-center">
            <div>
              <div className="text-xs font-semibold uppercase tracking-[0.24em]" style={{ color: dna.accentHue }}>{isPricing ? "Offer" : "Next step"}</div>
              <h2 className={`mt-4 text-4xl md:text-6xl font-semibold tracking-tight ${titleTone}`} style={{ fontFamily: dna.fontFamily }}>{polish(section.headline)}</h2>
              {section.body ? <p className={`mt-6 text-lg leading-relaxed ${bodyTone}`}>{polish(section.body)}</p> : null}
            </div>
            {items.length ? (
              <div className="space-y-3">
                {items.slice(0, 4).map((item, itemIndex) => (
                  <div key={itemIndex} className={`rounded-2xl border px-4 py-3 text-base ${mode === "light" ? "border-slate-200 bg-slate-50 text-slate-800" : "border-white/10 bg-black/20 text-slate-200"}`}>{polish(item)}</div>
                ))}
              </div>
            ) : null}
          </div>
        </div>
      </section>
    );
  }

  return (
    <section id={`section-${index}`} className={`border-t ${sectionTone(index, mode)} py-16 md:py-24 transition-opacity duration-700 ease-out`} style={{ animation: "fadeIn 0.8s ease-out backwards" }}>
      <div className="grid grid-cols-1 md:grid-cols-12 gap-8 md:gap-16">
        <div className="md:col-span-4 flex flex-col gap-4">
          <h2 className={`text-3xl md:text-4xl font-semibold tracking-tight ${titleTone}`} style={{ fontFamily: dna.fontFamily }}>
            {polish(section.headline)}
          </h2>
          {section.ctaLabel ? (
            <div className="mt-2 text-xs uppercase tracking-[0.2em] font-semibold" style={{ color: dna.accentHue }}>
              {section.ctaLabel}
            </div>
          ) : null}
        </div>

        <div className="md:col-span-8 flex flex-col gap-10">
          {section.body ? (
            <p className={`max-w-3xl text-lg md:text-xl leading-relaxed ${bodyTone}`}>
              {polish(section.body)}
            </p>
          ) : null}

          {items.length > 0 ? (
            isServices ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {items.slice(0, 6).map((item, itemIndex) => (
                  <div key={itemIndex} className={`border p-5 ${panelTone} ${dna.borderRadius}`}>
                    <div className="mb-8 h-1 w-10 rounded-full" style={{ backgroundColor: dna.accentHue }} />
                    <div className={`text-lg md:text-xl leading-relaxed ${titleTone}`}>
                      {polish(item)}
                    </div>
                  </div>
                ))}
              </div>
            ) : isProof ? (
              <div className="grid gap-4 md:grid-cols-2">
                {items.slice(0, 4).map((item, itemIndex) => {
                  const match = polish(item).match(/^([^:]+):(.*)$/);
                  const isQuote = item.includes('"');
                  return (
                    <div key={itemIndex} className={`border p-6 ${panelTone} ${dna.borderRadius}`}>
                      {match ? (
                        <>
                          <span className={`font-semibold block text-xl md:text-2xl mb-3 ${titleTone}`}>{match[1]}</span>
                          <span className={`${bodyTone} text-base md:text-lg leading-relaxed`}>{match[2]}</span>
                        </>
                      ) : (
                        <span className={`text-lg md:text-xl leading-relaxed ${titleTone} ${isQuote ? 'italic' : ''}`}>{polish(item)}</span>
                      )}
                    </div>
                  );
                })}
              </div>
            ) : (
              <ul className="space-y-4">
                {items.map((item, itemIndex) => (
                  <li key={itemIndex} className={`text-base md:text-lg flex gap-4 ${bodyTone}`}>
                    <span className="opacity-50 font-mono" style={{ color: dna.accentHue }}>—</span> {polish(item)}
                  </li>
                ))}
              </ul>
            )
          ) : null}
        </div>
      </div>
    </section>
  );
}

const PREVIEW_SESSION_KEY = "lenquant_preview_session_id";

function ensurePreviewSessionId(): string | null {
  if (typeof window === "undefined") return null;
  const existing = window.sessionStorage.getItem(PREVIEW_SESSION_KEY);
  if (existing) return existing;
  const nextId = typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2);
  window.sessionStorage.setItem(PREVIEW_SESSION_KEY, nextId);
  return nextId;
}

export default function PublicPreviewPage({ params }: { params: Promise<{ slug: string }> }) {
  const [site, setSite] = useState<GeneratedSite | null | undefined>(undefined);
  const { slug } = use(params);
  const previewSlug = normalizePreviewSlug(slug);
  const sessionRef = useRef<string | null>(null);
  const pagePath = `/sites/${previewSlug}`;

  useEffect(() => {
    sessionRef.current = sessionRef.current ?? ensurePreviewSessionId();
  }, []);

  useEffect(() => {
    let mounted = true;
    async function load() {
      const result = await getPublicSite(previewSlug);
      if (!mounted) return;
      setSite(result);
    }
    void load();
    return () => { mounted = false; };
  }, [previewSlug]);

  useEffect(() => {
    if (!site) return;
    const sessionId = sessionRef.current ?? ensurePreviewSessionId();
    if (!sessionId) return;
    sessionRef.current = sessionId;
    const base = { siteId: site.id, leadId: site.leadId, sessionId, pagePath };
    void sendAnalyticsEvent({ ...base, eventType: "site_opened", eventName: "Public preview opened" });
    void sendAnalyticsEvent({ ...base, eventType: "page_view", eventName: "Preview page view" });
  }, [site, pagePath]);

  function trackCta(eventType: AnalyticsEventType, label: string, href: string) {
    if (!site) return;
    const sessionId = sessionRef.current ?? ensurePreviewSessionId();
    if (!sessionId) return;
    sessionRef.current = sessionId;
    void sendAnalyticsEvent({
      siteId: site.id,
      leadId: site.leadId,
      sessionId,
      eventType,
      eventName: label,
      pagePath,
      metadata: { href }
    });
  }

  if (site === undefined) {
    return (
      <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(255,255,255,0.08),_transparent_22%),linear-gradient(180deg,_#0d1118_0%,_#070a0f_100%)] px-4 py-8 text-text">
        <div className="mx-auto flex min-h-[60vh] max-w-6xl items-center justify-center">
          <div className="rounded-3xl border border-white/10 bg-white/5 px-6 py-5 text-sm text-muted">Loading preview...</div>
        </div>
      </div>
    );
  }

  if (!site) {
    return (
      <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(255,255,255,0.08),_transparent_22%),linear-gradient(180deg,_#0d1118_0%,_#070a0f_100%)] px-4 py-8 text-text">
        <div className="mx-auto max-w-6xl">
          <EmptyState
            title="Preview not available"
            description="No website preview is available for this link yet. Please check the URL or create a preview from your workspace."
            action={
              <Button>
                <Link href="/nsa/leads">Back</Link>
              </Button>
            }
          />
        </div>
      </div>
    );
  }

  const mode = site.paletteMode;
  const textColor = mode === "light" ? "#0f172a" : "#f8fafc";
  const heroImg = heroImage(site);
  const dna = deriveDesignDNA(site);
  const screenshotPanelTone = mode === "light"
    ? "bg-white/70 border-slate-200 shadow-[0_24px_80px_rgba(15,23,42,0.08)]"
    : "bg-white/[0.045] border-white/10 shadow-[0_24px_90px_rgba(0,0,0,0.28)]";

  return (
    <div className={`min-h-screen relative ${mode === "light" ? "bg-slate-50" : "bg-[#05070a]"}`}>
      <div
        className="absolute inset-0 bg-shell-grid bg-shell-radial bg-[size:4rem_4rem] opacity-40 pointer-events-none"
        aria-hidden="true"
      />
      <div
        className="relative z-0 min-h-screen px-4 py-8 md:py-10"
        style={{ background: paletteBackground(mode), color: textColor }}
      >
        <div className="mx-auto max-w-7xl">
          {/* Quality Score Badge - Hidden on public preview */}

          {/* Screenshot Preview (optional) */}
          {site.screenshotRefs && site.screenshotRefs.length > 0 && (
            <div className="mb-12">
              <details className={`group border rounded-xl p-4 md:p-6 cursor-pointer transition-colors ${
                mode === "light"
                  ? "border-slate-200 bg-slate-50 hover:bg-slate-100"
                  : "border-white/10 bg-white/5 hover:bg-white/10"
              }`}>
                <summary className={`flex items-center gap-2 font-semibold text-sm select-none ${contentTone(mode)}`}>
                  <span className="transition-transform group-open:rotate-90">▶</span>
                  QA Screenshots & Analysis
                </summary>
                <div className="mt-4 space-y-4">
                  {site.screenshotRefs.map((ref, idx) => (
                    <div key={idx} className={`border rounded-lg overflow-hidden ${screenshotPanelTone}`}>
                      {ref.url && (
                        <>
                          <div className="relative w-full h-96 max-h-96">
                            <Image
                              src={ref.url}
                              alt={ref.label}
                              fill
                              className="object-cover"
                            />
                          </div>
                          <div className="p-4">
                            <p className={`text-xs font-medium ${contentTone(mode)}`}>{ref.label}</p>
                            {ref.notes && (
                              <p className={`text-sm mt-2 ${mutedTone(mode)}`}>{ref.notes}</p>
                            )}
                          </div>
                        </>
                      )}
                    </div>
                  ))}
                </div>
              </details>
            </div>
          )}

          <header className="relative py-16 md:py-32 flex flex-col justify-center min-h-[60vh]">
            {heroImg ? (
              <div className="pointer-events-none absolute inset-0 -z-10 overflow-hidden" aria-hidden="true">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={heroImg}
                  alt=""
                  className={`absolute right-0 top-1/2 hidden -translate-y-1/2 opacity-80 blur-[0.2px] drop-shadow-2xl md:block object-cover ${dna.borderRadius}`}
                  style={{
                    width: "min(50vw, 720px)",
                    height: "min(80vh, 800px)",
                    maskImage: dna.maskImage,
                    WebkitMaskImage: dna.maskImage,
                  }}
                />
              </div>
            ) : null}
            <h1
              style={{ fontFamily: dna.fontFamily }}
              className="max-w-[4xl] text-5xl md:text-7xl font-bold leading-[1.05] tracking-tight drop-shadow-sm"
            >
              {polish(site.heroVariant.headline)}
            </h1>
            <p className={`mt-8 max-w-2xl text-xl leading-relaxed ${mode === "light" ? "text-slate-600" : "text-slate-300"}`}>
              {polish(site.heroVariant.supportingLine)}
            </p>
            <div className="mt-12 flex flex-wrap gap-4">
              <Button
               
                style={{ backgroundColor: dna.accentHue, color: "#fff" }}
                className="hover:opacity-90 rounded-full px-8 py-3 text-lg border-none"
                onClick={() => trackCta("hero_cta_click", ensureClientCta(site.ctaStrategy.primary.label), site.ctaStrategy.primary.href)}
              >
                <Link href={site.ctaStrategy.primary.href}>
                  {ensureClientCta(site.ctaStrategy.primary.label)}
                </Link>
              </Button>
              <Button
               
                variant="secondary"
                className="rounded-full px-8 py-3 text-lg bg-transparent"
                style={{ borderColor: dna.accentHue, borderWidth: '1px', borderStyle: 'solid', color: mode === 'light' ? '#0f172a' : '#fff' }}
                onClick={() => trackCta("secondary_cta_click", ensureClientCta(site.ctaStrategy.secondary.label), site.ctaStrategy.secondary.href)}
              >
                <Link href={site.ctaStrategy.secondary.href}>{ensureClientCta(site.ctaStrategy.secondary.label)}</Link>
              </Button>
            </div>
          </header>

          <main>
            {site.sectionStack?.length ? (
              <nav className="mb-12 sticky top-4 z-20 flex w-full snap-x items-center gap-3 overflow-x-auto py-2 backdrop-blur-md">
                {site.sectionStack
                  .filter((s) => s.kind !== "gap")
                  .slice(0, 8)
                  .map((s, i) => (
                    <a
                      key={`nav-${i}`}
                      href={`#section-${i}`}
                      className={`whitespace-nowrap rounded-full border px-4 py-1.5 text-sm transition-colors ${
                        mode === "light"
                          ? "border-slate-300 bg-white/50 text-slate-700 hover:bg-slate-100 hover:border-slate-400"
                          : "border-white/10 bg-black/20 text-slate-300 hover:bg-white/10 hover:border-white/20 hover:text-white"
                      }`}
                    >
                      {polish(s.title || s.headline)}
                    </a>
                  ))}
              </nav>
            ) : null}

            <div id="sections" className="flex flex-col">
              {(site.sectionStack || [])
                .filter((s) => s.kind !== "gap")
                .map((section, index) => (
                  <div key={`${section.title}-${index}`}>
                    {renderSection(section, index, mode, dna)}
                  </div>
                ))}
            </div>

            <section id="contact" className={`mt-12 border-t ${sectionTone(0, mode)} py-20 text-center`}>
              <h2 className={`text-4xl font-semibold tracking-tight ${contentTone(mode)}`} style={{ fontFamily: dna.fontFamily }}>
                Ready to take the next step?
              </h2>
              <p className={`mt-6 text-xl max-w-2xl mx-auto ${mutedTone(mode)}`}>
                Get a closer look and decide if it fits your team.
              </p>
              <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
                <Button
                 
                  className="rounded-full px-8 py-3 text-lg hover:opacity-90 border-none"
                  style={{ backgroundColor: dna.accentHue, color: "#fff" }}
                  onClick={() => trackCta("hero_cta_click", ensureClientCta(site.ctaStrategy.primary.label), site.ctaStrategy.primary.href)}
                >
                  <Link href={site.ctaStrategy.primary.href}>{ensureClientCta(site.ctaStrategy.primary.label)}</Link>
                </Button>
                <Button
                 
                  variant="secondary"
                  className="rounded-full px-8 py-3 text-lg bg-transparent hover:bg-black/5"
                  style={{ borderColor: dna.accentHue, borderWidth: '1px', borderStyle: 'solid', color: mode === 'light' ? '#0f172a' : '#fff' }}
                  onClick={() => trackCta("secondary_cta_click", ensureClientCta(site.ctaStrategy.secondary.label), site.ctaStrategy.secondary.href)}
                >
                  <Link href={site.ctaStrategy.secondary.href}>{ensureClientCta(site.ctaStrategy.secondary.label)}</Link>
                </Button>
              </div>
            </section>
          </main>
        </div>
      </div>
      <style dangerouslySetInnerHTML={{__html: `
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @media (prefers-reduced-motion: reduce) {
          * {
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: 0.01ms !important;
            scroll-behavior: auto !important;
          }
        }
      `}} />
    </div>
  );
}
