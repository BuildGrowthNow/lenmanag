"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";

import { createSiteOverride, generateSite, republishSite } from "@/lib/api/sites";
import type { GeneratedSite } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

type SiteWorkspaceControlsProps = {
  siteId: string;
  site: GeneratedSite | null;
  hasApprovedBrief: boolean;
  hasExtraction: boolean;
};

const overrideScopes = ["copy", "layout", "brand", "cta", "motion", "style"] as const;

export function SiteWorkspaceControls({ siteId, site, hasApprovedBrief, hasExtraction }: SiteWorkspaceControlsProps) {
  const router = useRouter();
  const [busy, setBusy] = useState<"generate" | "republish" | "override" | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [scope, setScope] = useState<(typeof overrideScopes)[number]>("copy");
  const [path, setPath] = useState("hero.headline");
  const [value, setValue] = useState("");
  const [reason, setReason] = useState("");
  const [previousValue, setPreviousValue] = useState("");

  async function handleGenerate() {
    setBusy("generate");
    setMessage(null);
    try {
      await generateSite(siteId);
      setMessage("Preview generated from the approved brief.");
      router.refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not generate the preview.");
    } finally {
      setBusy(null);
    }
  }

  async function handleRepublish() {
    setBusy("republish");
    setMessage(null);
    try {
      await republishSite(siteId);
      setMessage("Preview republished with the stored overrides.");
      router.refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not republish the preview.");
    } finally {
      setBusy(null);
    }
  }

  async function handleOverride(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy("override");
    setMessage(null);
    try {
      await createSiteOverride(siteId, {
        scope,
        path: path.trim(),
        value: value.trim(),
        previousValue: previousValue.trim() || null,
        reason: reason.trim() || null
      });
      setMessage("Override stored and will survive regeneration.");
      setValue("");
      setReason("");
      setPreviousValue("");
      router.refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not save the override.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-3">
        <Button type="button" onClick={() => void handleGenerate()} disabled={!hasApprovedBrief || !hasExtraction || busy !== null}>
          {busy === "generate" ? "Generating..." : site ? "Regenerate preview" : "Generate preview"}
        </Button>
        <Button type="button" variant="secondary" onClick={() => void handleRepublish()} disabled={!site || busy !== null}>
          {busy === "republish" ? "Republishing..." : "Republish preview"}
        </Button>
      </div>
      <form onSubmit={(event) => void handleOverride(event)} className="space-y-3 rounded-2xl border border-line bg-panel-2 p-4">
        <div>
          <div className="text-xs uppercase tracking-[0.18em] text-muted">Structured override</div>
          <div className="mt-1 text-xs text-muted">Overrides are stored separately from the generated site so approved edits survive regeneration.</div>
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          <label className="space-y-2 text-sm">
            <span className="text-xs uppercase tracking-[0.18em] text-muted">Scope</span>
            <select className="h-10 w-full rounded-xl border border-line bg-panel px-3 text-sm text-text" value={scope} onChange={(event) => setScope(event.target.value as (typeof overrideScopes)[number])}>
              {overrideScopes.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>
          <label className="space-y-2 text-sm">
            <span className="text-xs uppercase tracking-[0.18em] text-muted">Path</span>
            <Input value={path} onChange={(event) => setPath(event.target.value)} placeholder="hero.headline or cta.primary.label" />
          </label>
        </div>
        <label className="space-y-2 text-sm">
          <span className="text-xs uppercase tracking-[0.18em] text-muted">Value</span>
          <Textarea value={value} onChange={(event) => setValue(event.target.value)} rows={3} placeholder="Enter the approved replacement value." />
        </label>
        <label className="space-y-2 text-sm">
          <span className="text-xs uppercase tracking-[0.18em] text-muted">Reason</span>
          <Input value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Why this override should persist." />
        </label>
        <label className="space-y-2 text-sm">
          <span className="text-xs uppercase tracking-[0.18em] text-muted">Previous value</span>
          <Input value={previousValue} onChange={(event) => setPreviousValue(event.target.value)} placeholder="Optional comparison value." />
        </label>
        <div className="flex flex-wrap gap-3">
          <Button type="submit" disabled={busy === "override" || !site}>
            {busy === "override" ? "Saving..." : "Save override"}
          </Button>
        </div>
        {!site ? <div className="text-xs text-muted">Generate the first preview before saving overrides.</div> : null}
      </form>
      {message ? <div className="text-xs leading-5 text-muted">{message}</div> : null}
    </div>
  );
}
