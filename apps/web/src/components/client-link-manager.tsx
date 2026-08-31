"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowDown, ArrowUp, Check, Copy, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getClientShare, getVariantsForLead, saveClientShare } from "@/lib/api/sites";
import type { GeneratedSite } from "@/lib/types";

function eligible(site: GeneratedSite) {
  return site.compilationStatus !== "failed" && site.readinessStatus !== "blocked" && Boolean(site.previewUrl || site.previewSlug);
}

export function ClientLinkManager({ leadId }: { leadId: string }) {
  const [sites, setSites] = useState<GeneratedSite[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [savedUrl, setSavedUrl] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    const [share, all] = await Promise.all([
      getClientShare(leadId),
      getVariantsForLead(leadId),
    ]);
    const available = all.filter(eligible).sort((a, b) => a.variantPosition - b.variantPosition);
    setSites(available);
    setSelected((share?.siteIds ?? []).filter((id) => available.some((site) => site.id === id)));
    setSavedUrl(share?.url ?? null);
  }, [leadId]);

  useEffect(() => { void load(); }, [load]);

  const selectedSites = useMemo(() => selected.map((id) => sites.find((site) => site.id === id)).filter(Boolean) as GeneratedSite[], [selected, sites]);
  const toggle = (id: string) => setSelected((current) => current.includes(id) ? current.filter((item) => item !== id) : current.length < 4 ? [...current, id] : current);
  const move = (index: number, delta: number) => {
    const next = [...selected];
    const target = index + delta;
    if (target < 0 || target >= next.length) return;
    [next[index], next[target]] = [next[target], next[index]];
    setSelected(next);
  };

  async function save() {
    if (selected.length < 1 || selected.length > 4) return;
    setSaving(true); setMessage(null);
    try {
      const share = await saveClientShare(leadId, selected);
      setSavedUrl(share.url); setMessage("Client link saved.");
    } catch (error) { setMessage(error instanceof Error ? error.message : "Could not save the client link."); }
    finally { setSaving(false); }
  }

  async function copy() {
    if (!savedUrl) return;
    try { await navigator.clipboard.writeText(savedUrl); setMessage("Client link copied."); }
    catch { setMessage("Copy failed. Select the link and copy it manually."); }
  }

  return <Card>
    <CardHeader><CardTitle>Client link</CardTitle></CardHeader>
    <CardContent className="space-y-4">
      <p className="text-sm text-muted">Choose 1–4 compiled website options. The saved order becomes the client gallery order.</p>
      {sites.length === 0 ? <p className="rounded-lg border border-yellow-500/20 bg-yellow-500/5 p-3 text-sm text-yellow-200">No compiled website is available yet. This action will become available after generation succeeds.</p> : <>
        <div className="space-y-2">{sites.map((site) => <label key={site.id} className="flex cursor-pointer items-center gap-3 rounded-lg border border-white/10 p-3 hover:bg-white/5">
          <input type="checkbox" checked={selected.includes(site.id)} onChange={() => toggle(site.id)} />
          <span className="flex-1 text-sm">{site.variantLabel || "Website option"}<span className="ml-2 text-xs text-muted">v{site.version}</span></span>
          <a href={site.previewUrl || `/st/${site.previewSlug}`} target="_blank" rel="noreferrer" className="text-muted hover:text-text" onClick={(event) => event.stopPropagation()}><ExternalLink className="h-4 w-4" /></a>
        </label>)}</div>
        {selectedSites.length > 0 && <div className="space-y-2 rounded-lg bg-white/5 p-3"><div className="text-xs uppercase tracking-wider text-muted">Gallery order</div>{selectedSites.map((site, index) => <div key={site.id} className="flex items-center gap-2 text-sm"><span className="w-16 text-muted">Option {index + 1}</span><span className="flex-1 truncate">{site.variantLabel}</span><Button size="icon" variant="ghost" disabled={index === 0} onClick={() => move(index, -1)}><ArrowUp className="h-4 w-4" /></Button><Button size="icon" variant="ghost" disabled={index === selectedSites.length - 1} onClick={() => move(index, 1)}><ArrowDown className="h-4 w-4" /></Button></div>)}</div>}
        <div className="flex flex-wrap gap-2"><Button onClick={() => void save()} disabled={saving || selected.length < 1}>{saving ? "Saving…" : "Save selection"}</Button>{savedUrl && <><Button variant="secondary" onClick={() => void copy()}><Copy className="mr-2 h-4 w-4" />Copy link</Button><a href={savedUrl} target="_blank" rel="noreferrer" className="inline-flex items-center rounded-md border border-white/10 px-3 text-sm text-muted hover:text-text">Preview gallery</a></>}</div>
      </>}
      {message && <p className="flex items-center gap-2 text-sm text-muted"><Check className="h-4 w-4 text-emerald-400" />{message}</p>}
    </CardContent>
  </Card>;
}
