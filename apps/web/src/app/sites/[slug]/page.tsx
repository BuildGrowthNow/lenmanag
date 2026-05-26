"use client";

import { useEffect, useState } from "react";
import { ExternalLink, Sparkles } from "lucide-react";
import Link from "next/link";

import { EmptyState } from "@/components/state/empty-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getSite } from "@/lib/api/sites";
import type { GeneratedSite, SiteSection } from "@/lib/types";

function paletteBackground(mode: string) {
  if (mode === "colorful") return "radial-gradient(circle at top, rgba(249,115,22,0.22), transparent 30%), linear-gradient(180deg, #08111f 0%, #040814 100%)";
  if (mode === "light") return "radial-gradient(circle at top, rgba(59,130,246,0.16), transparent 28%), linear-gradient(180deg, #f8fafc 0%, #e2e8f0 100%)";
  return "radial-gradient(circle at top, rgba(148,163,184,0.12), transparent 28%), linear-gradient(180deg, #0b0f14 0%, #05070a 100%)";
}

function sectionTone(index: number, mode: string) {
  if (mode === "colorful") return index % 2 === 0 ? "bg-white/7 border-white/10" : "bg-white/4 border-white/8";
  if (mode === "light") return index % 2 === 0 ? "bg-white/80 border-slate-300/80" : "bg-slate-100/80 border-slate-300/70";
  return index % 2 === 0 ? "bg-white/5 border-white/10" : "bg-white/3 border-white/8";
}

function contentTone(mode: string) {
  return mode === "light" ? "text-slate-900" : "text-text";
}

function mutedTone(mode: string) {
  return mode === "light" ? "text-slate-600" : "text-muted";
}

function renderSection(section: SiteSection, index: number, mode: string) {
  return (
    <div className={`rounded-[28px] border p-6 shadow-[0_20px_80px_rgba(0,0,0,0.18)] ${sectionTone(index, mode)}`}>
      <div className="flex flex-wrap items-center gap-2">
        <Badge className={mode === "light" ? "border-slate-300 bg-white/80 text-slate-900" : "bg-white/5 text-text"}>{section.eyebrow || section.kind}</Badge>
        <Badge className={mode === "light" ? "border-slate-300 bg-white/80 text-slate-900" : "bg-white/5 text-text"}>{section.evidence.inferenceLabel}</Badge>
      </div>
      <h2 className={`mt-4 text-2xl font-semibold tracking-tight ${contentTone(mode)}`}>{section.headline}</h2>
      <p className={`mt-3 max-w-2xl text-sm leading-6 ${mutedTone(mode)}`}>{section.body}</p>
      {section.items.length ? (
        <div className="mt-5 grid gap-3 md:grid-cols-2">
          {section.items.map((item) => (
            <div
              key={item}
              className={`rounded-2xl border px-4 py-3 text-sm ${mode === "light" ? "border-slate-300 bg-white/85 text-slate-900" : "border-white/10 bg-white/6 text-text"}`}
            >
              {item}
            </div>
          ))}
        </div>
      ) : null}
      {section.ctaLabel ? <div className={`mt-5 text-xs uppercase tracking-[0.22em] ${mutedTone(mode)}`}>{section.ctaLabel}</div> : null}
    </div>
  );
}

export default function PublicPreviewPage({ params }: { params: { slug: string } }) {
  const [site, setSite] = useState<GeneratedSite | null | undefined>(undefined);
  const slug = params.slug;

  useEffect(() => {
    let mounted = true;
    async function load() {
      const result = await getSite(slug);
      if (!mounted) return;
      setSite(result);
    }
    void load();
    return () => {
      mounted = false;
    };
  }, [slug]);

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
          <div className="mb-6 flex items-center justify-between">
            <div>
              <Badge>Preview runtime</Badge>
              <h1 style={{ fontFamily: "var(--font-heading)" }} className="mt-3 text-4xl font-semibold">
                /{slug}
              </h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
                The generated site has not been created yet. Use the admin workspace to generate a source-safe preview from the approved brief.
              </p>
            </div>
            <Badge className="bg-white/8">No preview</Badge>
          </div>
          <EmptyState
            title="Preview not available"
            description="There is no generated site document for this slug yet."
            action={
              <Button asChild>
                <Link href="/nsa/leads">Back to leads</Link>
              </Button>
            }
          />
        </div>
      </div>
    );
  }

  const mode = site.paletteMode;
  const textColor = mode === "light" ? "#0f172a" : "#f8fafc";
  const mutedColor = mode === "light" ? "#475569" : "#cbd5e1";
  const surfaceColor = mode === "light" ? "rgba(255,255,255,0.82)" : "rgba(255,255,255,0.04)";
  const borderColor = mode === "light" ? "rgba(148,163,184,0.45)" : "rgba(255,255,255,0.1)";

  return (
    <div style={{ background: paletteBackground(mode), color: textColor }} className="min-h-screen px-4 py-6">
      <div className="mx-auto max-w-7xl space-y-6">
        <header className={`rounded-[32px] border p-6 backdrop-blur ${mode === "light" ? "border-slate-300 bg-white/70" : "border-white/10 bg-white/5"}`}>
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <div className="flex flex-wrap gap-2">
                <Badge className={mode === "light" ? "border-slate-300 bg-white/80 text-slate-900" : "bg-white/5 text-text"}>Preview slug {site.previewSlug}</Badge>
                <Badge className={mode === "light" ? "border-slate-300 bg-white/80 text-slate-900" : "bg-white/5 text-text"}>v{site.version}</Badge>
                <Badge className={mode === "light" ? "border-slate-300 bg-white/80 text-slate-900" : "bg-white/5 text-text"}>{site.themeName}</Badge>
                <Badge className={mode === "light" ? "border-slate-300 bg-white/80 text-slate-900" : "bg-white/5 text-text"}>{site.paletteMode}</Badge>
              </div>
              <h1 style={{ fontFamily: "var(--font-heading)" }} className="mt-4 max-w-4xl text-5xl font-semibold tracking-tight">
                {site.heroVariant.headline}
              </h1>
              <p className={`mt-4 max-w-3xl text-base leading-7 ${mode === "light" ? "text-slate-700" : "text-slate-300"}`}>{site.heroVariant.supportingLine}</p>
              <div className="mt-4 flex flex-wrap gap-3">
                <Button asChild>
                  <Link href={site.ctaStrategy.primary.href}>
                    {site.ctaStrategy.primary.label}
                  </Link>
                </Button>
                <Button asChild variant="secondary">
                  <Link href={site.ctaStrategy.secondary.href}>
                    {site.ctaStrategy.secondary.label}
                  </Link>
                </Button>
              </div>
            </div>
            <div className={`rounded-3xl border p-5 ${mode === "light" ? "border-slate-300 bg-white/80" : "border-white/10 bg-white/5"}`}>
              <div className="text-xs uppercase tracking-[0.24em]" style={{ color: mutedColor }}>
                Generation notes
              </div>
              <div className="mt-2 space-y-2 text-sm">
                <div>Quality score: {site.qualityScore}</div>
                <div>Readiness: {site.readinessStatus}</div>
                <div>QA status: {site.qaStatus}</div>
                <div>Job id: {site.generationJobId || "Not recorded"}</div>
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                <Badge className={mode === "light" ? "border-slate-300 bg-white/80 text-slate-900" : "bg-white/5 text-text"}>{site.brandTokens.visualTone.value}</Badge>
                <Badge className={mode === "light" ? "border-slate-300 bg-white/80 text-slate-900" : "bg-white/5 text-text"}>{site.brandTokens.layoutDensity.value}</Badge>
              </div>
            </div>
          </div>
        </header>

        <main className="grid gap-5">
          <Card style={{ background: surfaceColor, borderColor }} className="overflow-hidden">
            <CardHeader>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <CardTitle style={{ color: textColor }}>Brand application</CardTitle>
                  <div className={`mt-1 text-sm ${mode === "light" ? "text-slate-700" : "text-muted"}`}>
                    Color, typography, and visual tone are all driven by extracted cues or explicit inference labels.
                  </div>
                </div>
                <Badge className={mode === "light" ? "border-slate-300 bg-white/80 text-slate-900" : "bg-white/5 text-text"}>
                  <Sparkles className="mr-1 h-3.5 w-3.5" />
                  Source-safe preview
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              {[
                ["Primary", site.brandTokens.primaryColor],
                ["Accent", site.brandTokens.accentColor],
                ["Typography", site.brandTokens.typography],
                ["Logo", site.brandTokens.logoAsset]
              ].map(([label, token]) => (
                <div key={label} className={`rounded-2xl border p-4 ${mode === "light" ? "border-slate-300 bg-white/80" : "border-white/10 bg-white/5"}`}>
                  <div className="text-xs uppercase tracking-[0.18em]" style={{ color: mutedColor }}>
                    {label}
                  </div>
                  {token ? (
                    <>
                      <div className="mt-2 text-sm" style={{ color: textColor }}>
                        {(token as { value: string }).value}
                      </div>
                      <div className="mt-1 text-xs" style={{ color: mutedColor }}>
                        {(token as { evidence: { inferenceLabel: string } }).evidence.inferenceLabel}
                      </div>
                    </>
                  ) : (
                    <div className="mt-2 text-sm" style={{ color: mutedColor }}>
                      No token recorded
                    </div>
                  )}
                </div>
              ))}
            </CardContent>
          </Card>

          <div className="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
            <div id="sections" className="space-y-5">
              {site.sectionStack.map((section, index) => (
                <div key={`${section.title}-${index}`}>{renderSection(section, index, mode)}</div>
              ))}
            </div>

            <div className="space-y-5">
              <Card id="source-notes" style={{ background: surfaceColor, borderColor }}>
                <CardHeader>
                  <CardTitle style={{ color: textColor }}>Source notes</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {site.sourceTraceability.length ? (
                    site.sourceTraceability.slice(0, 6).map((reference, index) => (
                      <div
                        key={`${reference.kind}-${index}`}
                        className={`rounded-2xl border p-3 text-sm ${mode === "light" ? "border-slate-300 bg-white/80" : "border-white/10 bg-white/5"}`}
                        style={{ color: textColor }}
                      >
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge className={mode === "light" ? "border-slate-300 bg-white/80 text-slate-900" : "bg-white/5 text-text"}>{reference.kind}</Badge>
                          <span>{reference.label}</span>
                        </div>
                        <div className="mt-2 text-xs" style={{ color: mutedColor }}>
                          {reference.sourceUrl}
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="text-sm" style={{ color: mutedColor }}>
                      No traceability metadata was stored with this preview.
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card style={{ background: surfaceColor, borderColor }}>
                <CardHeader>
                  <CardTitle style={{ color: textColor }}>Preview metadata</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3 text-sm">
                  <div>Preview URL: {site.previewUrl}</div>
                  <div>Generated: {new Date(site.updatedAt).toLocaleString()}</div>
                  <div>Theme rationale: {site.themeRationale}</div>
                  <div>Palette rationale: {site.paletteRationale}</div>
                  <div>
                    <Link className="inline-flex items-center gap-2 underline underline-offset-4" href={`/nsa/sites/${site.leadId}`}>
                      Open admin review <ExternalLink className="h-4 w-4" />
                    </Link>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>

          <Card id="contact" style={{ background: surfaceColor, borderColor }}>
            <CardHeader>
              <CardTitle style={{ color: textColor }}>Approved CTA path</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-3">
              <Button asChild>
                <Link href={site.ctaStrategy.primary.href}>{site.ctaStrategy.primary.label}</Link>
              </Button>
              <Button asChild variant="secondary">
                <Link href={site.ctaStrategy.secondary.href}>{site.ctaStrategy.secondary.label}</Link>
              </Button>
              <Button asChild variant="secondary">
                <Link href={site.ctaStrategy.footer.href}>{site.ctaStrategy.footer.label}</Link>
              </Button>
            </CardContent>
          </Card>
        </main>
      </div>
    </div>
  );
}
