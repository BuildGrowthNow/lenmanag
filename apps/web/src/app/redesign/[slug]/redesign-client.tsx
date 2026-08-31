"use client";

import Image from "next/image";
import type { RedesignPageData, RedesignVariant } from "./page";

function gridClass(count: number): string {
  if (count === 1) return "flex justify-center";
  if (count === 2) return "grid grid-cols-2 gap-6";
  if (count === 3) return "grid grid-cols-2 md:grid-cols-3 gap-6";
  return "grid grid-cols-2 lg:grid-cols-4 gap-6";
}

function cardMaxWidth(count: number): string {
  if (count === 1) return "max-w-[480px] w-full";
  return "";
}

function buildHeadline(
  companyName: string | null,
  contactName: string | null,
  count: number
): { headline: string; sub: string } {
  const company = companyName ?? "you";
  const greeting = contactName ? `Hey ${contactName}, ` : "";

  let headline: string;
  if (count === 1) {
    headline = `${greeting}We built something for ${company}.`;
  } else if (count === 2) {
    headline = `${greeting}Two directions for ${company}.`;
  } else {
    headline = `${greeting}We explored ${count} design directions for ${company}.`;
  }

  return {
    headline,
    sub: "Click any option to see it live.",
  };
}

function VariantCard({ variant }: { variant: RedesignVariant }) {
  const hasPreview = Boolean(variant.previewUrl);
  return (
    <div className={`group overflow-hidden rounded-2xl border border-white/[0.08] transition-all ${hasPreview ? "hover:scale-[1.02] hover:shadow-2xl hover:shadow-yellow-500/10" : "opacity-75"}`}>
      {hasPreview ? <a href={variant.previewUrl} target="_blank" rel="noopener noreferrer" className="block" aria-label={`Open Option ${variant.optionNumber}`}>
      <div className="aspect-[4/3] overflow-hidden bg-slate-800 flex items-center justify-center">
        {variant.screenshotUrl ? (
          <Image
            src={variant.screenshotUrl}
            alt={`Option ${variant.optionNumber} preview`}
            width={720}
            height={540}
            className="w-full h-full object-cover object-top"
            unoptimized
          />
        ) : (
          <div className="flex flex-col items-center gap-2 text-zinc-400 group-hover:text-yellow-400 transition-colors">
            <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" />
            </svg>
            <span className="text-sm font-medium">Screenshot coming soon</span>
          </div>
        )}
      </div>
      </a> : <div className="flex aspect-[4/3] items-center justify-center bg-slate-800 px-6 text-center text-sm text-zinc-400">This option is temporarily unavailable.</div>}
      <div className="border-t border-white/[0.08] bg-slate-900/80 px-4 py-3">
        <div className="font-semibold text-white">Option {variant.optionNumber}</div>
        {variant.variantLabel ? <div className="mt-1 text-sm text-zinc-400">{variant.variantLabel}</div> : null}
        {hasPreview ? <div className="mt-2 text-xs text-yellow-400">Click to preview live ↗</div> : null}
      </div>
    </div>
  );
}

export function RedesignClient({ data }: { data: RedesignPageData }) {
  const { companyName, contactName, logoUrl, variants } = data;
  const { headline, sub } = buildHeadline(companyName, contactName, variants.length);

  return (
    <div className="relative min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      {/* Grid overlay */}
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)",
          backgroundSize: "80px 80px",
        }}
      />

      <div className="relative z-10 mx-auto max-w-6xl px-6 py-16">
        {/* Logo / company name header */}
        <div className="mb-12 flex flex-col items-center gap-4 text-center">
          {logoUrl ? (
            <Image
              src={logoUrl}
              alt={companyName ?? "Logo"}
              width={160}
              height={40}
              className="h-10 w-auto object-contain"
              unoptimized
            />
          ) : (
            <p className="text-2xl font-bold text-zinc-100">
              {companyName ?? ""}
            </p>
          )}

          <h1 className="mt-2 max-w-2xl text-3xl font-semibold tracking-tight text-white sm:text-4xl">
            {headline}
          </h1>
          <p className="text-base text-zinc-400">{sub}</p>
        </div>

        {/* Screenshot grid */}
        <div className={gridClass(variants.length)}>
          {variants.map((v) => (
            <div key={v.siteId} className={cardMaxWidth(variants.length)}>
              <VariantCard variant={v} />
            </div>
          ))}
        </div>

        {/* CTA section */}
        <div className="mt-16 flex flex-col items-center gap-6 text-center">
          <div className="h-px w-24 bg-white/10" />
          <p className="text-lg text-zinc-300">
            Love one of these? Let&apos;s build your final version.
          </p>
          <a
            href={process.env.NEXT_PUBLIC_CALENDLY_URL || "https://calendly.com/lenquant/sites"}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-block rounded-full bg-yellow-500 px-8 py-3 text-sm font-semibold text-slate-900 transition-colors hover:bg-yellow-400"
          >
            Book a call
          </a>
        </div>

        {/* Footer */}
        <p className="mt-16 text-center text-xs text-zinc-600">Built by LenQuant</p>
      </div>
    </div>
  );
}
