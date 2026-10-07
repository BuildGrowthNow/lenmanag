"use client";

import Image from "next/image";
import { useState } from "react";
import { resolveBookingUrl } from "@/lib/booking";
import type { RedesignPageData, RedesignVariant } from "./page";

function BusinessIdentity({ logoUrl, companyName }: { logoUrl: string | null; companyName: string | null }) {
  const [logoFailed, setLogoFailed] = useState(false);
  const name = companyName?.trim() || "Business";
  const src = logoUrl?.trim();

  if (!src || logoFailed) {
    return <p className="text-2xl font-bold text-zinc-100">{name}</p>;
  }

  return (
    <Image
      src={src}
      alt={name}
      width={160}
      height={40}
      className="h-10 w-auto object-contain"
      unoptimized
      onError={() => setLogoFailed(true)}
    />
  );
}

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
    headline = `${greeting}We explored one design direction for ${company}.`;
  } else {
    headline = `${greeting}We explored ${count} design directions for ${company}.`;
  }

  return {
    headline,
    sub: "Click any option to see it live.",
  };
}

function VariantCard({ variant }: { variant: RedesignVariant }) {
  return (
    <a
      href={variant.previewUrl}
      target="_blank"
      rel="noopener noreferrer"
      className="group block rounded-2xl overflow-hidden border border-white/[0.08] transition-all duration-300 hover:scale-[1.02] hover:shadow-2xl hover:shadow-yellow-500/10 cursor-pointer"
    >
      <div className="aspect-[4/3] overflow-hidden bg-slate-800 flex items-center justify-center">
        {variant.screenshotUrl ? (
          <Image
            src={variant.screenshotUrl}
            alt="Site preview"
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
            <span className="text-sm font-medium">Click to preview</span>
          </div>
        )}
      </div>
      <div className="space-y-1.5 p-4 text-left">
        <h2 className="text-base font-semibold text-zinc-100">{variant.variantLabel}</h2>
        {variant.variantDescription ? (
          <p className="text-sm leading-relaxed text-zinc-400">{variant.variantDescription}</p>
        ) : null}
      </div>
    </a>
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
          <BusinessIdentity key={logoUrl} logoUrl={logoUrl} companyName={companyName} />

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

        {/* Offer and next step */}
        <section
          aria-labelledby="redesign-offer-heading"
          className="mx-auto mt-12 max-w-4xl rounded-3xl border border-white/10 bg-white/[0.03] p-6 text-center sm:p-8"
        >
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-yellow-400">
            Your custom landing page
          </p>
          <h2 id="redesign-offer-heading" className="mt-3 text-2xl font-semibold text-white">
            Love one of these? Let&apos;s build your final version.
          </h2>
          <dl className="mt-7 grid gap-5 sm:grid-cols-3 sm:gap-0 sm:divide-x sm:divide-white/10">
            <div>
              <dt className="text-sm text-zinc-400">One-time price</dt>
              <dd className="mt-1 text-3xl font-bold text-yellow-400">$1,000</dd>
            </div>
            <div>
              <dt className="text-sm text-zinc-400">Delivery</dt>
              <dd className="mt-1 text-3xl font-bold text-white">3 days</dd>
            </div>
            <div>
              <dt className="text-sm text-zinc-400">Revisions &amp; support</dt>
              <dd className="mt-1 text-3xl font-bold text-white">7 days</dd>
            </div>
          </dl>
          <div className="mt-7 rounded-2xl border border-yellow-500/15 bg-yellow-500/5 px-4 py-4">
            <p className="text-sm font-semibold text-yellow-400">100% money-back guarantee</p>
            <p className="mt-1 text-sm leading-relaxed text-zinc-300">
              Not satisfied within 7 days of delivery? Get a full refund on the base landing page.
            </p>
          </div>
          <a
            href={resolveBookingUrl(data.callUrl)}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-7 inline-block rounded-full bg-yellow-500 px-8 py-3 text-sm font-semibold text-slate-900 transition-colors hover:bg-yellow-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-yellow-400"
          >
            Book a call
          </a>
          <p className="mt-3 text-sm text-zinc-400">Free 30-minute call · No commitment</p>
          <p className="mx-auto mt-5 max-w-2xl text-xs leading-relaxed text-zinc-500">
            Delivery starts after scope approval and receipt of your content. Additional pages and features
            are scoped on the call. Guarantee covers the base service.{' '}
            <a href="/terms" target="_blank" rel="noopener noreferrer" className="underline underline-offset-2 hover:text-zinc-300">
              See terms
            </a>.
          </p>
        </section>

        {/* Footer */}
        <p className="mt-16 text-center text-xs text-zinc-600">Built by LenQuant</p>
      </div>
    </div>
  );
}
