"use client";

import { useState } from "react";
import Link from "next/link";

type SiteVariant = {
  id: string;
  leadId: string;
  variantLabel: string;
  variantType: string;
  variantPosition: number;
  previewSlug: string;
  previewUrl: string;
  compiledBundleUrl: string | null;
  staticHtml: string | null;
  compilationStatus: string;
  readinessStatus: string;
  qualityScore: number;
};

type CompareClientProps = {
  variants: SiteVariant[];
  companyName: string;
  leadId: string;
  appUrl: string;
};

function VariantLabel({ position }: { position: number }) {
  const labels = ["Option A", "Option B", "Option C", "Option D"];
  return labels[position] ?? `Option ${position + 1}`;
}

function ReadinessBadge({ status }: { status: string }) {
  const cls =
    status === "published" || status === "ready_to_publish"
      ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
      : status === "ready_for_review"
        ? "bg-yellow-500/20 text-yellow-300 border border-yellow-500/30"
        : "bg-zinc-500/20 text-zinc-400 border border-zinc-500/30";
  const label = status.replace(/_/g, " ");
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-medium uppercase tracking-wider ${cls}`}>
      {label}
    </span>
  );
}

export function CompareClient({ variants, companyName, appUrl }: CompareClientProps) {
  const [activeVariant, setActiveVariant] = useState<string>(variants[0]?.id ?? "");
  const [copied, setCopied] = useState(false);
  const [viewMode, setViewMode] = useState<"side-by-side" | "single">(
    variants.length === 1 ? "single" : "side-by-side"
  );

  const activeVariantData = variants.find((v) => v.id === activeVariant) ?? variants[0];

  async function handleCopyLink() {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // fallback: do nothing
    }
  }

  function previewSrc(variant: SiteVariant) {
    return variant.previewUrl || `/st/${variant.previewSlug}`;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-zinc-100">
      {/* Grid overlay */}
      <div
        className="pointer-events-none fixed inset-0 opacity-[0.025]"
        style={{
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.5) 1px, transparent 1px)",
          backgroundSize: "60px 60px",
        }}
      />

      {/* Header */}
      <header className="relative z-10 border-b border-white/8 bg-slate-950/80 backdrop-blur-xl">
        <div className="mx-auto flex max-w-screen-2xl items-center justify-between gap-4 px-6 py-4">
          <div className="flex items-center gap-4">
            <Link href={appUrl} className="flex items-center gap-2">
              <span className="text-lg font-bold tracking-tight text-yellow-400">LenQuant</span>
            </Link>
            <div className="h-5 w-px bg-white/15" />
            <div>
              <div className="text-sm font-semibold text-zinc-100">{companyName}</div>
              <div className="text-xs text-zinc-400">
                {variants.length} variant{variants.length !== 1 ? "s" : ""} · custom landing page previews
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {variants.length > 1 && (
              <div className="flex items-center gap-1 rounded-lg border border-white/10 bg-white/5 p-1">
                <button
                  onClick={() => setViewMode("side-by-side")}
                  className={`rounded-md px-3 py-1 text-xs font-medium transition-all ${
                    viewMode === "side-by-side"
                      ? "bg-yellow-500 text-slate-900 shadow"
                      : "text-zinc-400 hover:text-zinc-200"
                  }`}
                >
                  Side by side
                </button>
                <button
                  onClick={() => setViewMode("single")}
                  className={`rounded-md px-3 py-1 text-xs font-medium transition-all ${
                    viewMode === "single"
                      ? "bg-yellow-500 text-slate-900 shadow"
                      : "text-zinc-400 hover:text-zinc-200"
                  }`}
                >
                  Single
                </button>
              </div>
            )}

            <button
              onClick={() => void handleCopyLink()}
              className="flex items-center gap-2 rounded-lg border border-white/15 bg-white/5 px-4 py-2 text-sm font-medium text-zinc-300 transition-all hover:border-yellow-500/40 hover:bg-yellow-500/10 hover:text-yellow-300 active:scale-95"
            >
              {copied ? (
                <>
                  <svg className="h-4 w-4 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                  Copied!
                </>
              ) : (
                <>
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                  Share link
                </>
              )}
            </button>
          </div>
        </div>

        {/* Variant tabs */}
        {variants.length > 1 && (
          <div className="mx-auto max-w-screen-2xl px-6 pb-0">
            <div className="flex gap-0 border-t border-white/8">
              {variants.map((v, i) => (
                <button
                  key={v.id}
                  onClick={() => {
                    setActiveVariant(v.id);
                    if (viewMode === "side-by-side" && variants.length === 1) {
                      setViewMode("single");
                    }
                  }}
                  className={`relative flex items-center gap-2 border-r border-white/8 px-5 py-3 text-sm font-medium transition-all last:border-r-0 ${
                    activeVariant === v.id
                      ? "bg-yellow-500/10 text-yellow-300 after:absolute after:bottom-0 after:left-0 after:right-0 after:h-0.5 after:bg-yellow-500"
                      : "text-zinc-400 hover:bg-white/5 hover:text-zinc-200"
                  }`}
                >
                  <span className="h-5 w-5 rounded-full bg-yellow-500/20 text-center text-[10px] font-bold leading-5 text-yellow-400">
                    {String.fromCharCode(65 + i)}
                  </span>
                  {v.variantLabel || `Option ${i + 1}`}
                  <ReadinessBadge status={v.readinessStatus} />
                </button>
              ))}
            </div>
          </div>
        )}
      </header>

      {/* Main content */}
      <main className="relative z-10 mx-auto max-w-screen-2xl px-6 py-6">
        {viewMode === "side-by-side" && variants.length > 1 ? (
          <div
            className="grid gap-4"
            style={{
              gridTemplateColumns: `repeat(${Math.min(variants.length, 3)}, 1fr)`,
            }}
          >
            {variants.map((v, i) => (
              <VariantCard
                key={v.id}
                variant={v}
                index={i}
                isActive={activeVariant === v.id}
                onSelect={() => setActiveVariant(v.id)}
              />
            ))}
          </div>
        ) : (
          <SingleVariantView variant={activeVariantData} />
        )}
      </main>

      {/* Footer */}
      <footer className="relative z-10 border-t border-white/8 py-6">
        <div className="mx-auto max-w-screen-2xl px-6 text-center">
          <p className="text-xs text-zinc-500">
            Built by{" "}
            <span className="font-semibold text-yellow-400">LenQuant</span>
            {" "}· AI-powered landing page previews for B2B outreach
          </p>
        </div>
      </footer>
    </div>
  );
}

function VariantCard({
  variant,
  index,
  isActive,
  onSelect,
}: {
  variant: SiteVariant;
  index: number;
  isActive: boolean;
  onSelect: () => void;
}) {
  const label = <VariantLabel position={variant.variantPosition ?? index} />;
  const src = variant.previewUrl || `/st/${variant.previewSlug}`;

  return (
    <div
      className={`group flex flex-col overflow-hidden rounded-2xl border transition-all ${
        isActive
          ? "border-yellow-500/50 shadow-lg shadow-yellow-500/10"
          : "border-white/10 hover:border-white/20"
      }`}
    >
      {/* Card header */}
      <div className="flex items-center justify-between gap-3 border-b border-white/8 bg-slate-900/60 px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-yellow-500/20 text-[11px] font-bold text-yellow-400">
            {String.fromCharCode(65 + index)}
          </span>
          <span className="text-sm font-medium text-zinc-200">
            {variant.variantLabel || String(label)}
          </span>
          <ReadinessBadge status={variant.readinessStatus} />
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={onSelect}
            className={`rounded-md px-2.5 py-1 text-xs font-medium transition-all ${
              isActive
                ? "bg-yellow-500/20 text-yellow-300"
                : "bg-white/5 text-zinc-400 hover:bg-white/10 hover:text-zinc-200"
            }`}
          >
            {isActive ? "Selected" : "Select"}
          </button>
          <a
            href={src}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 rounded-md bg-white/5 px-2.5 py-1 text-xs text-zinc-400 transition-all hover:bg-white/10 hover:text-zinc-200"
          >
            Open
            <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </a>
        </div>
      </div>

      {/* Iframe */}
      <div className="relative aspect-[9/16] w-full overflow-hidden bg-slate-950 sm:aspect-[4/5]">
        <iframe
          src={src}
          title={variant.variantLabel || `Option ${index + 1}`}
          className="h-full w-full border-0"
          style={{ transform: "scale(0.5)", transformOrigin: "top left", width: "200%", height: "200%" }}
          loading="lazy"
          sandbox="allow-scripts allow-same-origin allow-forms"
        />
        <div className="pointer-events-none absolute inset-0" />
      </div>
    </div>
  );
}

function SingleVariantView({ variant }: { variant: SiteVariant }) {
  const src = variant.previewUrl || `/st/${variant.previewSlug}`;

  return (
    <div className="flex flex-col gap-4">
      {/* Controls bar */}
      <div className="flex items-center justify-between gap-3 rounded-2xl border border-white/10 bg-slate-900/60 px-5 py-3">
        <div className="flex items-center gap-3">
          <span className="text-sm font-medium text-zinc-200">
            {variant.variantLabel || "Preview"}
          </span>
          <ReadinessBadge status={variant.readinessStatus} />
          {variant.qualityScore > 0 && (
            <span className="text-xs text-zinc-400">
              Quality: {variant.qualityScore}/100
            </span>
          )}
        </div>
        <a
          href={src}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 rounded-lg bg-yellow-500 px-4 py-2 text-sm font-semibold text-slate-900 transition-all hover:bg-yellow-400 active:scale-95"
        >
          Open full screen
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
          </svg>
        </a>
      </div>

      {/* Full-height iframe */}
      <div className="overflow-hidden rounded-2xl border border-white/10 bg-slate-950" style={{ height: "calc(100vh - 240px)", minHeight: 600 }}>
        <iframe
          src={src}
          title={variant.variantLabel || "Preview"}
          className="h-full w-full border-0"
          loading="eager"
          sandbox="allow-scripts allow-same-origin allow-forms"
        />
      </div>
    </div>
  );
}
