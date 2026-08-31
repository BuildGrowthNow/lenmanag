"use client";
import { useState } from "react";

type SiteVariant = { siteId: string; variantLabel: string | null; variantPosition: number; optionNumber: number; previewUrl: string; screenshotUrl: string };

export function CompareClient({ variants, companyName }: { variants: SiteVariant[]; companyName: string }) {
  const [active, setActive] = useState(variants[0]?.siteId ?? "");
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState(false);
  const activeVariant = variants.find((variant) => variant.siteId === active) ?? variants[0];
  async function copyLink() { try { await navigator.clipboard.writeText(window.location.href); setCopied(true); setCopyError(false); setTimeout(() => setCopied(false), 2000); } catch { setCopyError(true); } }
  return <main className="min-h-screen bg-slate-950 px-4 py-8 text-zinc-100 sm:px-6">
    <header className="mx-auto mb-8 flex max-w-6xl flex-wrap items-center justify-between gap-4 border-b border-white/10 pb-5"><div><div className="text-lg font-bold text-yellow-400">LenQuant</div><div className="mt-1 text-sm text-zinc-200">{companyName}</div><div className="text-xs text-zinc-500">Selected website options</div></div><button onClick={() => void copyLink()} className="rounded-lg border border-white/15 px-4 py-2 text-sm hover:border-yellow-500/50">{copied ? "Copied!" : "Copy link"}</button></header>
    {copyError ? <p className="mx-auto mb-4 max-w-6xl rounded-lg bg-rose-500/10 p-3 text-sm text-rose-200">Copy failed. You can copy the address from your browser.</p> : null}
    <div className="mx-auto max-w-6xl">{variants.length > 1 ? <div className="mb-5 flex flex-wrap gap-2">{variants.map((variant) => <button key={variant.siteId} onClick={() => setActive(variant.siteId)} className={`rounded-full px-3 py-2 text-sm ${active === variant.siteId ? "bg-yellow-500 text-slate-900" : "bg-white/10 text-zinc-300"}`}>Option {variant.optionNumber}</button>)}</div> : null}
      <div className="grid gap-5 sm:grid-cols-2">{variants.map((variant) => <article key={variant.siteId} className={`overflow-hidden rounded-2xl border ${active === variant.siteId ? "border-yellow-500/50" : "border-white/10"}`}><div className="flex items-center justify-between border-b border-white/10 px-4 py-3"><div><div className="font-semibold">Option {variant.optionNumber}</div>{variant.variantLabel ? <div className="text-xs text-zinc-400">{variant.variantLabel}</div> : null}</div><a href={variant.previewUrl} target="_blank" rel="noreferrer" className="text-xs text-yellow-400">Open ↗</a></div><div className="aspect-[4/3] bg-slate-900">{variant.previewUrl ? <iframe src={variant.previewUrl} title={`Option ${variant.optionNumber}`} className="h-full w-full border-0" loading="lazy" sandbox="allow-scripts allow-same-origin allow-forms" /> : <div className="flex h-full items-center justify-center text-sm text-zinc-500">Preview unavailable</div>}</div></article>)}</div>
      {activeVariant ? <div className="mt-6 text-center"><a href={activeVariant.previewUrl} target="_blank" rel="noreferrer" className="inline-flex rounded-lg bg-yellow-500 px-5 py-3 text-sm font-semibold text-slate-900">Open selected option full screen ↗</a></div> : null}
    </div>
  </main>;
}
