"use client";

import Link from "next/link";
import { AlertTriangle, ArrowLeft, CheckCircle2, Circle, XCircle, ExternalLink, Copy, Check } from "lucide-react";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { PageFrame } from "@/components/shell/page-frame";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { LeadBriefReview } from "@/components/lead-brief-review";
import { LeadExtractionControls } from "@/components/lead-extraction-controls";
import { LeadVariantsView } from "@/components/lead-variants-view";
import { PipelineActivityLog } from "@/components/pipeline-activity-log";
import { getLead, getLeadMasterBrief, getLeadExtraction, getLeadPages, getLeadAnalysis } from "@/lib/api/leads";
import { getSite } from "@/lib/api/sites";
import { evaluateExtractionHealth } from "@/lib/extraction-health";
import type { LeadDetail, ExtractionSnapshot, MasterBrief, GeneratedSite, PipelineStage, ExtractionAnalysisResponse } from "@/lib/types";
import { cn } from "@/lib/utils";

// ── Helpers ───────────────────────────────────────────────────────────────

function stageBadgeClass(stage: PipelineStage): string {
  switch (stage) {
    case "extracting":
    case "extracted":
      return "border-blue-500/40 bg-blue-500/10 text-blue-200";
    case "briefing":
    case "brief_ready":
      return "border-yellow-500/40 bg-yellow-500/10 text-yellow-200";
    case "generating":
    case "qa":
      return "border-purple-500/40 bg-purple-500/10 text-purple-200";
    case "ready":
      return "border-emerald-500/40 bg-emerald-500/10 text-emerald-200";
    case "published":
      return "border-emerald-400/60 bg-emerald-400/15 text-emerald-100 font-semibold";
    case "needs_attention":
      return "border-rose-500/40 bg-rose-500/10 text-rose-200";
    case "archived":
      return "border-white/10 bg-white/5 text-muted";
    default:
      return "border-white/15 bg-white/5 text-muted";
  }
}

const STAGE_LABEL: Record<PipelineStage, string> = {
  new: "New",
  extracting: "Extracting",
  extracted: "Extracted",
  briefing: "Briefing",
  brief_ready: "Brief ready",
  generating: "Generating",
  qa: "QA",
  ready: "Ready",
  published: "Published",
  needs_attention: "Needs attention",
  archived: "Archived",
};

function formatDateTime(value: string | null | undefined) {
  if (!value) return "Not recorded";
  return new Date(value).toLocaleString();
}

function progressWidth(progress: number) {
  return `${Math.max(0, Math.min(100, progress))}%`;
}

function ProgressBar({ progress, label }: { progress: number; label: string }) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between gap-3 text-xs text-muted">
        <span>{label}</span>
        <span>{progress}%</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-white/8">
        <div className="h-full rounded-full bg-accent transition-all" style={{ width: progressWidth(progress) }} />
      </div>
    </div>
  );
}

// ── Stage workspace ───────────────────────────────────────────────────────

function StageWorkspace({
  lead,
  extraction,
  brief,
  site,
}: {
  lead: LeadDetail;
  extraction: ExtractionSnapshot | null;
  brief: MasterBrief | null;
  site: GeneratedSite | null;
}) {
  const stage = lead.pipelineStage;

  if (stage === "extracting") {
    const job = lead.latestJob;
    return (
      <WorkspaceCard title="Extracting website">
        {job ? (
          <div className="space-y-4">
            <ProgressBar progress={job.progress} label={job.step} />
            {extraction && extraction.pagesCrawled > 0 ? (
              <div className="space-y-1.5">
                <div className="text-xs uppercase tracking-[0.18em] text-muted">Pages found so far</div>
                {extraction.pageInventory.slice(0, 6).map((p) => (
                  <div key={p.url} className="flex items-center gap-2 text-sm">
                    <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-emerald-400" />
                    <span className="truncate text-muted">{p.url}</span>
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        ) : (
          <p className="text-sm text-muted">Extraction queued…</p>
        )}
      </WorkspaceCard>
    );
  }

  if (stage === "briefing") {
    const job = lead.latestJob;
    return (
      <WorkspaceCard title="Generating brief">
        {job ? (
          <ProgressBar progress={job.progress} label={job.step} />
        ) : (
          <p className="text-sm text-muted">Brief generation running…</p>
        )}
      </WorkspaceCard>
    );
  }

  if (stage === "generating") {
    const job = lead.latestJob;
    return (
      <WorkspaceCard title="Generating site">
        {job ? (
          <ProgressBar progress={job.progress} label={job.step} />
        ) : (
          <p className="text-sm text-muted">Site generation running…</p>
        )}
      </WorkspaceCard>
    );
  }

  if (stage === "brief_ready" || stage === "extracted") {
    return (
      <WorkspaceCard title={brief ? "Brief — ready for review" : "Extraction complete"}>
        {brief ? (
          <LeadBriefReview
            leadId={lead.id}
            brief={brief}
            extractionHealth={evaluateExtractionHealth(extraction)}
          />
        ) : (
          <div className="space-y-3">
            <p className="text-sm text-muted">
              Extraction complete with confidence {extraction?.confidenceScore ?? 0}%.
              Generate the brief to continue.
            </p>
            <LeadExtractionControls leadId={lead.id} extraction={extraction} />
          </div>
        )}
      </WorkspaceCard>
    );
  }

  if (stage === "qa") {
    const score = site?.qualityScore ?? 0;
    const hasScreenshotQa = (site?.screenshotRefs?.length ?? 0) > 0;
    return (
      <WorkspaceCard title="Quality review">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-xs uppercase tracking-[0.18em] text-muted">Quality score</div>
              <div className={cn("mt-1 text-3xl font-semibold", score >= 90 ? "text-emerald-300" : score >= 75 ? "text-yellow-300" : "text-rose-300")}>
                {hasScreenshotQa ? `${score}` : `~${score}`}
                <span className="text-base font-normal text-muted"> / 100{!hasScreenshotQa ? " (no visual QA)" : ""}</span>
              </div>
            </div>
            {site && site.previewSlug ? (
              <Link href={site.previewUrl || `/st/${site.previewSlug}`} target="_blank" className={buttonVariants({ variant: "secondary" })}>Preview ↗</Link>
            ) : (
              <Button variant="secondary" disabled>Preview (loading...)</Button>
            )}
          </div>
          {site ? (
            <div className="space-y-2">
              {site.reviewRubric.slice(0, 5).map((check) => (
                <div key={check.key} className="flex items-start gap-2 text-sm">
                  {check.status === "pass" ? (
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" />
                  ) : check.status === "warn" ? (
                    <Circle className="mt-0.5 h-4 w-4 shrink-0 text-yellow-400" />
                  ) : (
                    <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-400" />
                  )}
                  <span className={check.status === "fail" ? "text-rose-300" : "text-text"}>
                    {check.label}
                  </span>
                </div>
              ))}
            </div>
          ) : null}
          <div className="flex gap-2 pt-2">
            <Link href={`/app/sites/${lead.id}`} className={buttonVariants({ variant: "ghost" })}>Open site workspace</Link>
          </div>
        </div>
      </WorkspaceCard>
    );
  }

  if (stage === "ready") {
    const score = site?.qualityScore ?? 0;
    return (
      <WorkspaceCard title="Ready to publish">
        <div className="space-y-4">
          <p className="text-sm text-text">
            Site passed QA with a score of{" "}
            <span className="font-semibold text-emerald-300">{score}/100</span>.
          </p>
          <div className="flex flex-wrap gap-2">
            {site && site.previewSlug ? (
              <Link href={site.previewUrl || `/st/${site.previewSlug}`} target="_blank" className={buttonVariants({ variant: "secondary" })}>Preview ↗</Link>
            ) : (
              <Button variant="secondary" disabled>Preview (loading...)</Button>
            )}
            <Link href={`/app/sites/${lead.id}`} className={buttonVariants()}>Open site workspace →</Link>
          </div>
        </div>
      </WorkspaceCard>
    );
  }

  if (stage === "published") {
    return (
      <WorkspaceCard title="Published">
        <div className="space-y-4">
          {site && site.previewUrl ? (
            <a href={site.previewUrl} target="_blank" rel="noreferrer" className="text-accent hover:underline break-all text-sm">
              {site.previewUrl} ↗
            </a>
          ) : (
            <p className="text-sm text-muted">Site preview URL not available yet</p>
          )}
          {site?.publishedAt ? (
            <p className="text-xs text-muted">Published {formatDateTime(site.publishedAt)}</p>
          ) : null}
          <div className="flex flex-wrap gap-2">
            <Link href="/app/messages" className={buttonVariants({ variant: "secondary" })}>View messages →</Link>
            <Link href="/app/analytics" className={buttonVariants({ variant: "secondary" })}>View analytics →</Link>
          </div>
        </div>
      </WorkspaceCard>
    );
  }

  if (stage === "needs_attention") {
    const reason = lead.pipelineStatusDetail ?? lead.latestJob?.errorMessage ?? "An error occurred.";
    return (
      <WorkspaceCard title="Blocked" accent="rose">
        <div className="space-y-4">
          <div className="flex items-start gap-2 rounded-xl border border-rose-500/20 bg-rose-500/5 p-3">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-rose-400" />
            <p className="text-sm text-rose-300">{reason}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <LeadExtractionControls leadId={lead.id} extraction={extraction} />
          </div>
        </div>
      </WorkspaceCard>
    );
  }

  // Default: new / unknown — show extraction controls
  return (
    <WorkspaceCard title="Start pipeline">
      <div className="space-y-3">
        <p className="text-sm text-muted">
          {lead.pipelineMode === "auto"
            ? "This lead is in auto mode — extraction starts automatically on creation."
            : "This lead is in manual mode. Start extraction to begin."}
        </p>
        <LeadExtractionControls leadId={lead.id} extraction={extraction} />
      </div>
    </WorkspaceCard>
  );
}

function WorkspaceCard({
  title,
  children,
  accent,
}: {
  title: string;
  children: React.ReactNode;
  accent?: "rose";
}) {
  return (
    <div
      className={cn(
        "rounded-2xl border p-5",
        accent === "rose"
          ? "border-rose-500/20 bg-rose-500/5"
          : "border-line bg-panel-2"
      )}
    >
      <div className="mb-4 text-sm font-medium uppercase tracking-[0.2em] text-muted">{title}</div>
      {children}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────

export default function LeadDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const router = useRouter();
  const [id, setId] = useState<string | null>(null);
  const [lead, setLead] = useState<LeadDetail | null>(null);
  const [extraction, setExtraction] = useState<ExtractionSnapshot | null>(null);
  const [analysis, setAnalysis] = useState<ExtractionAnalysisResponse | null>(null);
  const [pages, setPages] = useState<{ pages: any[] } | null>(null);
  const [brief, setBrief] = useState<MasterBrief | null>(null);
  const [site, setSite] = useState<GeneratedSite | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [showClientLinks, setShowClientLinks] = useState(false);
  const [copiedLink, setCopiedLink] = useState<string | null>(null);

  // Load params
  useEffect(() => {
    let mounted = true;
    async function loadParams() {
      const p = await params;
      if (mounted) setId(p.id);
    }
    void loadParams();
    return () => { mounted = false; };
  }, [params]);

  // Initial data load
  useEffect(() => {
    if (!id) return;
    let mounted = true;

    async function loadData() {
      try {
        const [leadData, extractionData, pagesData, briefData, siteData, analysisData] = await Promise.all([
          getLead(id),
          getLeadExtraction(id),
          getLeadPages(id),
          getLeadMasterBrief(id),
          getSite(id),
          getLeadAnalysis(id),
        ]);

        if (!mounted) return;

        setLead(leadData);
        setExtraction(extractionData);
        setPages(pagesData);
        setBrief(briefData);
        setSite(siteData);
        setAnalysis(analysisData);
        const sharingStages: PipelineStage[] = ["qa", "ready", "published"];
        setShowClientLinks(sharingStages.includes(leadData.pipelineStage));
        setLoading(false);
      } catch (error) {
        console.error("Failed to load lead data:", error);
        setLoadError(true);
        setLoading(false);
      }
    }

    void loadData();
    return () => { mounted = false; };
  }, [id]);

  // Auto-refresh polling when jobs are running
  useEffect(() => {
    if (!id || !lead) return;

    const hasRunningJob = lead.latestJob?.status === "running";
    const isGenerating = lead.pipelineStage === "generating" || lead.pipelineStage === "extracting" || lead.pipelineStage === "briefing";

    if (!hasRunningJob && !isGenerating) return;

    const pollInterval = setInterval(async () => {
      try {
        const [updatedLead, updatedSite, updatedAnalysis] = await Promise.all([
          getLead(id),
          getSite(id),
          getLeadAnalysis(id),
        ]);

        setLead(updatedLead);
        if (updatedSite) setSite(updatedSite);
        if (updatedAnalysis) setAnalysis(updatedAnalysis);

        // Stop polling if job completed
        if (updatedLead?.latestJob?.status !== "running") {
          router.refresh();
        }
      } catch (error) {
        console.error("Polling error:", error);
      }
    }, 5000); // Poll every 5 seconds

    return () => clearInterval(pollInterval);
  }, [id, lead, router]);

  if (loading) {
    return (
      <PageFrame eyebrow="Lead detail" title="Loading..." description="">
        <div className="text-sm text-muted">Loading lead details...</div>
      </PageFrame>
    );
  }

  if (loadError) {
    return (
      <PageFrame eyebrow="Lead detail" title="Error loading lead" description="">
        <div className="text-sm text-muted">
          Failed to load lead data. Please try refreshing.{" "}
          <Link href="/app/leads" className="text-accent hover:underline">Back to leads</Link>
        </div>
      </PageFrame>
    );
  }

  if (!lead) {
    return (
      <PageFrame eyebrow="Lead detail" title={`Lead: ${id}`} description="Lead not found.">
        <div className="text-sm text-muted">
          No lead record found for this ID.{" "}
          <Link href="/app/leads" className="text-accent hover:underline">Back to leads</Link>
        </div>
      </PageFrame>
    );
  }

  const pageInventory = pages?.pages ?? extraction?.pageInventory ?? [];
  const brandCues = extraction?.brandAssetCues ?? [];
  const gapItems = extraction?.gapItems ?? [];

  const appUrl = typeof window !== "undefined" ? window.location.origin : "https://sites.lenquant.com";
  const redesignUrl = lead.redesignSlug ? `${appUrl}/redesign/${lead.redesignSlug}` : null;
  const compareUrl = `${appUrl}/compare/${lead.id}`;

  const handleCopyLink = async (url: string) => {
    try {
      await navigator.clipboard.writeText(url);
      setCopiedLink(url);
      setTimeout(() => setCopiedLink(null), 2000);
    } catch (error) {
      console.error("Failed to copy link:", error);
    }
  };

  return (
    <PageFrame
      eyebrow="Lead detail"
      title={lead.companyName ?? lead.normalizedDomain ?? "Unnamed lead"}
      description={lead.normalizedDomain}
    >
      {/* Header bar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Link href="/app/leads" className="flex items-center gap-1 text-sm text-muted hover:text-text transition-colors">
            <ArrowLeft className="h-4 w-4" />
            Leads
          </Link>
          <Badge
            className={cn(stageBadgeClass(lead.pipelineStage), "ml-2")}
          >
            {STAGE_LABEL[lead.pipelineStage]}
          </Badge>
          <Badge className="border-white/20 bg-white/5 text-xs text-muted">
            {lead.pipelineMode === "auto" ? "Auto" : "Manual"}
          </Badge>
        </div>

        {/* Client sharing buttons */}
        {showClientLinks && (
          <div className="flex items-center gap-2">
            {redesignUrl && (
              <>
                <a
                  href={redesignUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={cn(
                    buttonVariants({ variant: "secondary", size: "sm" }),
                    "flex items-center gap-1.5"
                  )}
                >
                  <ExternalLink className="h-3.5 w-3.5" />
                  View Gallery
                </a>
                <button
                  onClick={() => void handleCopyLink(redesignUrl)}
                  className={cn(
                    buttonVariants({ variant: "ghost", size: "sm" }),
                    "flex items-center gap-1.5"
                  )}
                  title="Copy gallery link"
                >
                  {copiedLink === redesignUrl ? (
                    <Check className="h-3.5 w-3.5 text-emerald-400" />
                  ) : (
                    <Copy className="h-3.5 w-3.5" />
                  )}
                </button>
              </>
            )}
            <a
              href={compareUrl}
              target="_blank"
              rel="noopener noreferrer"
              className={cn(
                buttonVariants({ variant: "secondary", size: "sm" }),
                "flex items-center gap-1.5"
              )}
            >
              <ExternalLink className="h-3.5 w-3.5" />
              Compare Variants
            </a>
            <button
              onClick={() => void handleCopyLink(compareUrl)}
              className={cn(
                buttonVariants({ variant: "ghost", size: "sm" }),
                "flex items-center gap-1.5"
              )}
              title="Copy compare link"
            >
              {copiedLink === compareUrl ? (
                <Check className="h-3.5 w-3.5 text-emerald-400" />
              ) : (
                <Copy className="h-3.5 w-3.5" />
              )}
            </button>
          </div>
        )}
      </div>

      {/* Two-column layout */}
      <div className="grid gap-4 xl:grid-cols-[35%_65%]">

        {/* Left column — identity panels */}
        <div className="space-y-4">

          {/* Identity card */}
          <Card>
            <CardHeader>
              <CardTitle>Identity</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <Row label="Website" value={lead.websiteUrl} mono />
              <Row label="Domain" value={lead.normalizedDomain} mono />
              {lead.industry ? <Row label="Industry" value={lead.industry} /> : null}
              <Row label="Source" value={lead.sourceType} />
              <Row label="Added" value={formatDateTime(lead.createdAt)} />
              <Row label="Version" value={`v${lead.version}`} />
            </CardContent>
          </Card>

          {/* Notes card */}
          <Card>
            <CardHeader>
              <CardTitle>Notes</CardTitle>
            </CardHeader>
            <CardContent>
              {lead.notes ? (
                <p className="whitespace-pre-wrap text-sm text-text">{lead.notes}</p>
              ) : (
                <p className="text-sm text-muted italic">No notes.</p>
              )}
            </CardContent>
          </Card>

          {/* Pipeline Activity Log */}
          <PipelineActivityLog
            events={lead.pipelineEvents ?? []}
            defaultExpanded={false}
            maxCollapsedEvents={5}
          />

          {/* Source refs (collapsed) */}
          {lead.sourceRefs.length > 0 ? (
            <details className="rounded-2xl border border-line bg-panel-2 p-4">
              <summary className="cursor-pointer text-xs uppercase tracking-[0.18em] text-muted hover:text-text">
                {lead.sourceRefs.length} source ref{lead.sourceRefs.length !== 1 ? "s" : ""} ▾
              </summary>
              <div className="mt-3 space-y-2">
                {lead.sourceRefs.map((ref, i) => (
                  <div key={i} className="rounded-xl border border-line bg-panel px-3 py-2 text-xs">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge>{ref.sourceType}</Badge>
                      <span className="text-muted">{ref.sourceRef ?? "No ref"}</span>
                    </div>
                    <div className="mt-1 text-muted">{formatDateTime(ref.importedAt)}</div>
                  </div>
                ))}
              </div>
            </details>
          ) : null}

          {/* Job history (collapsed) */}
          <details className="rounded-2xl border border-line bg-panel-2 p-4">
            <summary className="cursor-pointer text-xs uppercase tracking-[0.18em] text-muted hover:text-text">
              View job history ▾
            </summary>
            <div className="mt-3 space-y-3">
              {lead.jobs.length ? (
                lead.jobs.map((job) => (
                  <div key={job.id} className="rounded-xl border border-line bg-panel p-3 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-medium text-text">{job.step}</span>
                      <Badge
                        className={
                          job.status === "running"
                            ? "border-blue-500/40 bg-blue-500/10 text-blue-200"
                            : job.status === "failed"
                              ? "border-rose-500/40 bg-rose-500/10 text-rose-200"
                              : job.status === "completed"
                                ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-200"
                                : "border-white/15 bg-white/5 text-muted"
                        }
                      >
                        {job.status}
                      </Badge>
                    </div>
                    <div className="mt-1 text-muted">{job.jobType} · {job.id.slice(0, 8)}</div>
                    {job.errorMessage ? (
                      <div className="mt-1 text-rose-300">{job.errorMessage}</div>
                    ) : null}
                    <div className="mt-2">
                      <ProgressBar progress={job.progress} label={`${job.progress}%`} />
                    </div>
                    <div className="mt-2 flex gap-4 text-muted">
                      <span>Started: {formatDateTime(job.startedAt)}</span>
                      <span>Finished: {formatDateTime(job.finishedAt)}</span>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-sm text-muted">No jobs yet.</p>
              )}
            </div>
          </details>
        </div>

        {/* Right column — stage workspace */}
        <div className="space-y-4">
          <StageWorkspace lead={lead} extraction={extraction} brief={brief} site={site} />

          {/* Variants section */}
          <LeadVariantsView leadId={lead.id} />

          {/* Extraction evidence (always accessible, collapsed) */}
          {extraction ? (
            <details className="rounded-2xl border border-line bg-panel-2 p-4">
              <summary className="cursor-pointer text-xs uppercase tracking-[0.18em] text-muted hover:text-text">
                Extraction evidence ▾
              </summary>
              <div className="mt-4 space-y-4 text-sm">
                <div className="grid gap-3 sm:grid-cols-2">
                  <div>
                    <div className="text-xs uppercase tracking-[0.18em] text-muted">Crawl</div>
                    <div className="mt-1 text-text">
                      {extraction.pagesCrawled} / {extraction.pagesDiscovered} pages
                    </div>
                    <div className="mt-0.5 text-xs text-muted">Confidence: {extraction.confidenceScore}%</div>
                  </div>
                  <div>
                    <div className="text-xs uppercase tracking-[0.18em] text-muted">Status</div>
                    <div className="mt-1 text-text">{extraction.crawlStatus}</div>
                    <div className="mt-0.5 text-xs text-muted">Sitemap: {extraction.sitemapStatus}</div>
                  </div>
                </div>

                {/* Analysis Results */}
                {analysis && analysis.analysis ? (
                  <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4">
                    <div className="text-xs uppercase tracking-[0.18em] text-emerald-300 mb-2">AI Analysis</div>
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-muted">Confidence</span>
                        <span className="font-semibold text-emerald-300">{analysis.analysis.confidence}%</span>
                      </div>
                      {analysis.analysis.valueProposition ? (
                        <div>
                          <div className="text-xs text-muted mb-1">Value Proposition:</div>
                          <p className="text-xs text-text">{analysis.analysis.valueProposition}</p>
                        </div>
                      ) : null}
                      {analysis.analysis.positioning ? (
                        <div>
                          <div className="text-xs text-muted mb-1">Positioning:</div>
                          <p className="text-xs text-text">{analysis.analysis.positioning}</p>
                        </div>
                      ) : null}
                      {analysis.analysis.services && analysis.analysis.services.length > 0 ? (
                        <div className="pt-2">
                          <div className="text-xs text-muted mb-1">Services Detected:</div>
                          <div className="flex flex-wrap gap-1.5">
                            {analysis.analysis.services.slice(0, 5).map((service, idx) => (
                              <Badge key={idx} className="border-emerald-500/30 bg-emerald-500/10 text-emerald-200 text-xs">
                                {service}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      ) : null}
                      {analysis.analysis.tone ? (
                        <div className="text-xs">
                          <span className="text-muted">Tone: </span>
                          <span className="text-text">{analysis.analysis.tone}</span>
                        </div>
                      ) : null}
                    </div>
                  </div>
                ) : null}

                {gapItems.length > 0 ? (
                  <div>
                    <div className="text-xs uppercase tracking-[0.18em] text-muted mb-2">Gaps</div>
                    <div className="flex flex-wrap gap-1.5">
                      {gapItems.map((g) => (
                        <Badge key={g} className="border-amber-500/30 bg-amber-500/10 text-amber-200">{g}</Badge>
                      ))}
                    </div>
                  </div>
                ) : null}

                {brandCues.length > 0 ? (
                  <div>
                    <div className="text-xs uppercase tracking-[0.18em] text-muted mb-2">Brand cues</div>
                    <div className="flex flex-wrap gap-1.5">
                      {brandCues.slice(0, 8).map((cue, i) => (
                        <Badge key={i}>{cue.assetType}: {cue.label}</Badge>
                      ))}
                    </div>
                  </div>
                ) : null}

                {pageInventory.length > 0 ? (
                  <div>
                    <div className="text-xs uppercase tracking-[0.18em] text-muted mb-2">Pages crawled</div>
                    <div className="space-y-1.5">
                      {pageInventory.slice(0, 8).map((p) => (
                        <div key={p.url} className="flex items-center gap-2 text-xs">
                          <Badge className={p.status === "crawled" ? "border-emerald-500/30 bg-emerald-500/5 text-emerald-300" : "border-rose-500/30 bg-rose-500/5 text-rose-300"}>
                            {p.status}
                          </Badge>
                          <span className="truncate text-muted">{p.url}</span>
                          <span className="shrink-0 text-muted">{p.confidence}%</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}

              </div>
            </details>
          ) : null}
        </div>
      </div>
    </PageFrame>
  );
}

// ── Small helper ──────────────────────────────────────────────────────────

function Row({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <span className="shrink-0 text-xs uppercase tracking-[0.15em] text-muted">{label}</span>
      <span className={cn("text-right text-text", mono && "break-all font-mono text-xs")}>{value}</span>
    </div>
  );
}
