"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import { ExternalLink, RefreshCw, CheckCircle2, Clock, AlertTriangle, XCircle } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getVariantsForLead, isPreviewUsable, previewPath, recaptureScreenshot } from "@/lib/api/sites";
import type { GeneratedSite, PipelineEvent, SiteReadinessStatus, VariantType } from "@/lib/types";
import { cn } from "@/lib/utils";

type VariantsViewProps = {
  leadId: string;
  pipelineEvents?: PipelineEvent[];
  requestedVariants?: VariantType[];
};

const VARIANT_LABELS: Record<VariantType, { name: string; description: string }> = {
  html_v1: { name: "Professional", description: "Clean corporate design with subtle gradients" },
  html_v2: { name: "Bold", description: "Vibrant colors and dynamic layouts" },
  html_v3: { name: "Creative", description: "Unique artistic direction" },
  nextjs: { name: "Next.js", description: "Full React-based component site" },
};

const READINESS_LABELS: Record<string, string> = {
  blocked: "Blocked",
  needs_review: "Needs review",
  ready_for_review: "Ready for QA",
  ready_to_publish: "Ready to publish",
  published: "Published",
};

function StatusIcon({ status }: { status: SiteReadinessStatus }) {
  switch (status) {
    case "ready_to_publish":
    case "published":
      return <CheckCircle2 className="h-4 w-4 text-emerald-400" />;
    case "ready_for_review":
      return <Clock className="h-4 w-4 text-blue-400" />;
    case "needs_review":
      return <AlertTriangle className="h-4 w-4 text-amber-400" />;
    case "blocked":
      return <XCircle className="h-4 w-4 text-rose-400" />;
    default:
      return <Clock className="h-4 w-4 text-muted" />;
  }
}

function readinessBadgeClass(status: SiteReadinessStatus): string {
  if (status === "published") return "border-emerald-400/60 bg-emerald-400/15 text-emerald-100 font-semibold";
  if (status === "ready_to_publish") return "border-emerald-500/40 bg-emerald-500/10 text-emerald-200";
  if (status === "ready_for_review") return "border-sky-500/40 bg-sky-500/10 text-sky-200";
  if (status === "needs_review") return "border-amber-500/40 bg-amber-500/10 text-amber-200";
  return "border-rose-500/40 bg-rose-500/10 text-rose-200";
}

function ReadinessBadge({ status }: { status: SiteReadinessStatus }) {
  return (
    <Badge className={readinessBadgeClass(status)}>
      {READINESS_LABELS[status] ?? status}
    </Badge>
  );
}

function VariantCard({ site, onRefresh }: { site: GeneratedSite; onRefresh: () => void }) {
  const variantType = site.variantType || "nextjs";
  const variantInfo = VARIANT_LABELS[variantType];
  const previewUrl = previewPath(site);
  const screenshotUrl = site.screenshotRefs?.[0]?.url ?? null;
  const [refreshing, setRefreshing] = useState(false);
  const [countdown, setCountdown] = useState(0);

  useEffect(() => {
    if (countdown > 0) {
      const timer = setTimeout(() => setCountdown(countdown - 1), 1000);
      return () => clearTimeout(timer);
    } else if (countdown === 0 && refreshing) {
      setRefreshing(false);
      onRefresh();
    }
  }, [countdown, refreshing, onRefresh]);

  async function handleRefreshScreenshot() {
    try {
      setRefreshing(true);
      setCountdown(20);
      await recaptureScreenshot(site.id);
    } catch (error) {
      console.error("Failed to refresh screenshot:", error);
      setRefreshing(false);
      setCountdown(0);
    }
  }

  const usable = isPreviewUsable(site);
  return (
    <Card className="group relative overflow-hidden border-line bg-panel hover:border-white/20 transition-colors">
      {/* Thumbnail */}
      {usable ? <a href={previewUrl} target="_blank" rel="noopener noreferrer" className="block relative h-36 w-full overflow-hidden bg-panel-2">
        {screenshotUrl ? (
          <Image
            src={screenshotUrl}
            alt={`Preview of ${site.variantTitle || site.variantLabel || variantInfo.name}`}
            fill
            className="object-cover object-top transition-transform duration-300 group-hover:scale-105"
            unoptimized
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-muted">
            <ExternalLink className="h-5 w-5" />
          </div>
        )}
      </a> : <div className="flex h-36 items-center justify-center bg-panel-2 px-4 text-center text-sm text-rose-300">Preview unavailable — this variant was not published.</div>}
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <CardTitle className="text-base font-medium text-text truncate">
              {site.variantTitle || site.variantLabel || variantInfo.name}
            </CardTitle>
            <p className="text-xs text-muted mt-0.5">{site.variantDescription || variantInfo.description}</p>
          </div>
          <div className="flex items-center gap-1.5">
            <StatusIcon status={site.readinessStatus} />
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex flex-wrap gap-2">
          <ReadinessBadge status={site.readinessStatus} />
        </div>

        {usable && site.qualityScoreSource === "visual" && site.qualityScore !== undefined && site.qualityScore !== null && (
          <div className="flex items-center gap-2 text-sm">
            <span className="text-muted">Quality Score:</span>
            <span className={cn(
              "font-medium",
              site.qualityScore >= 80 ? "text-emerald-400" :
              site.qualityScore >= 60 ? "text-amber-400" : "text-rose-400"
            )}>
              {site.qualityScore}%
            </span>
          </div>
        )}

        <div className="flex flex-col gap-2 pt-2 border-t border-line">
          {usable ? <a
            href={previewUrl}
            target="_blank"
            rel="noopener noreferrer"
            className={cn(
              "inline-flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
              "border border-accent/40 bg-accent/10 text-accent hover:bg-accent/20"
            )}
          >
            <ExternalLink className="h-4 w-4" />
            Preview
          </a> : <div className="rounded-lg border border-rose-500/20 bg-rose-500/5 px-3 py-2 text-center text-sm text-rose-300">No Preview or client link is available.</div>}
          {usable && <button
            onClick={() => void handleRefreshScreenshot()}
            disabled={refreshing}
            className={cn(
              "inline-flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
              refreshing
                ? "border border-blue-500/40 bg-blue-500/10 text-blue-300 cursor-wait"
                : "border border-white/15 bg-white/5 text-muted hover:bg-white/10 hover:text-text"
            )}
          >
            <RefreshCw className={cn("h-4 w-4", refreshing && "animate-spin")} />
            {refreshing ? `Refreshing... ${countdown}s` : "Refresh Screenshot"}
          </button>}
        </div>
      </CardContent>
    </Card>
  );
}

export function LeadVariantsView({ leadId, pipelineEvents = [], requestedVariants = [] }: VariantsViewProps) {
  const [variants, setVariants] = useState<GeneratedSite[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      setError(null);
      try {
        const data = await getVariantsForLead(leadId);
        const sorted = [...data].sort((a, b) => (a.variantPosition ?? 99) - (b.variantPosition ?? 99));
        setVariants(sorted);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load variants");
      } finally {
        setLoading(false);
      }
    }
    void loadData();
  }, [leadId]);

  async function refreshVariants() {
    setLoading(true);
    setError(null);
    try {
      const data = await getVariantsForLead(leadId);
      const sorted = [...data].sort((a, b) => (a.variantPosition ?? 99) - (b.variantPosition ?? 99));
      setVariants(sorted);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load variants");
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <Card className="border-line bg-panel">
        <CardHeader>
          <CardTitle className="text-lg">Site Variants</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8 text-muted">
            <RefreshCw className="h-5 w-5 animate-spin mr-2" />
            Loading variants...
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="border-line bg-panel">
        <CardHeader>
          <CardTitle className="text-lg">Site Variants</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <AlertTriangle className="h-8 w-8 text-rose-400 mb-2" />
            <p className="text-rose-400 text-sm">{error}</p>
            <Button variant="secondary" className="mt-3" onClick={refreshVariants}>
              Retry
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (variants.length === 0) {
    return (
      <Card className="border-line bg-panel">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-lg">Site Variants</CardTitle>
          <Button variant="ghost" size="sm" onClick={refreshVariants}>
            <RefreshCw className="h-4 w-4" />
          </Button>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-8 text-center text-muted">
            {requestedVariants.some((variant) => pipelineEvents.some((event) => event.variantType === variant && event.eventType === "site_generation_failed")) ? (
              <>
                <p className="text-rose-300">Generation failed — no website was published.</p>
                <p className="mt-1 max-w-xl text-xs">{pipelineEvents.find((event) => event.eventType === "site_generation_failed" && event.variantType)?.detail ?? "Review the pipeline activity for the actionable failure."}</p>
              </>
            ) : (
              <>
                <p>No site variants generated yet.</p>
                <p className="text-xs mt-1">Variants will appear here once generation completes.</p>
              </>
            )}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-line bg-panel">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-lg">Site Variants ({variants.length})</CardTitle>
        <div className="flex items-center gap-2">
          <Link href={`/compare/${leadId}`} target="_blank" className="inline-flex items-center gap-2 rounded-md border border-accent/40 bg-accent/10 px-3 py-2 text-sm text-accent hover:bg-accent/20">
            Compare variants ↗
          </Link>
          <Button variant="ghost" size="sm" onClick={refreshVariants}>
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {variants.map((variant) => (
            <VariantCard key={variant.id} site={variant} onRefresh={refreshVariants} />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
