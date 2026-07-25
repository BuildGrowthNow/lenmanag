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
  return (
    <a
      href={variant.previewUrl}
      target="_blank"
      rel="noopener noreferrer"
      className="group block rounded-2xl overflow-hidden border border-white/[0.08] transition-all duration-300 hover:scale-[1.02] hover:shadow-2xl hover:shadow-yellow-500/10 cursor-pointer"
    >
      <div className="aspect-[4/3] overflow-hidden bg-slate-800">
        <Image
          src={variant.screenshotUrl}
          alt="Site preview"
          width={720}
          height={540}
          className="w-full h-full object-cover object-top"
          unoptimized
        />
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
            href="https://calendly.com/lenquant/sites"
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
