import Link from "next/link";
import { ExternalLink, Sparkles, ShieldAlert } from "lucide-react";

import { EmptyState } from "@/components/state/empty-state";
import { PageFrame } from "@/components/shell/page-frame";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { SiteWorkspaceControls } from "@/components/site-workspace-controls";
import { SiteExportControls } from "@/components/site-export-controls";
import { ApplyThemeButton } from "@/components/apply-theme-button";
import { OverrideDiffBadgeWrapper } from "@/components/override-diff-badge-wrapper";
import { RefinementPromptInput } from "@/components/refinement-prompt-input";
import { PromptHistory } from "@/components/prompt-history";
import { getLead, getLeadMasterBrief, getLeadExtraction } from "@/lib/api/leads";
import {
  getSite,
  getSiteCompare,
  getSiteVersions,
  getThemes,
  getSiteExportHistory,
} from "@/lib/api/sites";
import type {
  GeneratedSite,
  GeneratedSiteVersion,
  SiteQualityCheck,
  ThemeVariant,
  OverrideDiff,
  SiteSection,
  BriefSourceReference,
} from "@/lib/types";
import { disableOverrideAction } from "./actions";

// ── Helpers ────────────────────────────────────────────────────────────────

function qualityLabel(score: number) {
  if (score >= 90) return "Pass";
  if (score >= 75) return "Review";
  if (score >= 55) return "Needs work";
  return "Blocked";
}

function qualityBadgeClass(score: number) {
  if (score >= 90) return "border-emerald-500/40 bg-emerald-500/10 text-emerald-100";
  if (score >= 75) return "border-yellow-500/40 bg-yellow-500/10 text-yellow-100";
  if (score >= 55) return "border-orange-500/40 bg-orange-500/10 text-orange-100";
  return "border-rose-500/40 bg-rose-500/10 text-rose-100";
}

function readinessBadgeClass(status: string) {
  if (status === "published") return "border-emerald-400/60 bg-emerald-400/15 text-emerald-100 font-semibold";
  if (status === "ready_to_publish") return "border-emerald-500/40 bg-emerald-500/10 text-emerald-100";
  if (status === "ready_for_review") return "border-sky-500/40 bg-sky-500/10 text-sky-100";
  if (status === "needs_review") return "border-amber-500/40 bg-amber-500/10 text-amber-100";
  return "border-rose-500/40 bg-rose-500/10 text-rose-100";
}

function qaBadgeClass(status: string) {
  if (status === "pass") return "border-emerald-500/40 bg-emerald-500/10 text-emerald-100";
  if (status === "warn") return "border-amber-500/40 bg-amber-500/10 text-amber-100";
  return "border-rose-500/40 bg-rose-500/10 text-rose-100";
}

function paletteClass(mode: string) {
  if (mode === "colorful") return "border-fuchsia-500/40 bg-fuchsia-500/10 text-fuchsia-100";
  if (mode === "light") return "border-sky-500/40 bg-sky-500/10 text-sky-100";
  return "border-zinc-500/40 bg-zinc-500/10 text-zinc-100";
}

function themeCardTone(theme: ThemeVariant) {
  if (theme.themeKey === "color-study") return "border-fuchsia-500/30 bg-fuchsia-500/8";
  if (theme.themeKey === "minimal-luxe") return "border-zinc-500/30 bg-zinc-500/8";
  if (theme.themeKey === "editorial-frame") return "border-emerald-500/30 bg-emerald-500/8";
  return "border-sky-500/30 bg-sky-500/8";
}

function formatDateTime(value: string | null | undefined) {
  return value ? new Date(value).toLocaleString() : "Not recorded";
}

function findDiffByPath(diffs: OverrideDiff[], path: string): OverrideDiff | undefined {
  return diffs.find((d) => d.path === path);
}

function qualityScoreDisplay(site: GeneratedSite | null): string {
  if (!site) return "—";
  if (site.readinessStatus === "blocked") return "Blocked";
  const hasScreenshotQA = site.screenshotRefs && site.screenshotRefs.length > 0;
  const score = site.qualityScore ?? 0;
  if (!hasScreenshotQA) {
    if (score === 0) return "— / 100";
    return `~${score} / 100`;
  }
  return `${score} / 100`;
}

function summarizeChecks(checks: SiteQualityCheck[]) {
  return {
    failures: checks.filter((c) => c.status === "fail").length,
    warnings: checks.filter((c) => c.status === "warn").length,
    passes: checks.filter((c) => c.status === "pass").length,
  };
}

// ── Tab sub-components ─────────────────────────────────────────────────────

function OverviewTab({ site }: { site: GeneratedSite }) {
  const checks = site.reviewRubric ?? [];
  const summary = summarizeChecks(checks);
  const hasScreenshotQA = site.screenshotRefs && site.screenshotRefs.length > 0;
  const score = site.qualityScore ?? 0;

  return (
    <div className="space-y-4">
      {/* Score panel */}
      <div className="rounded-2xl border border-line bg-panel-2 p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="text-xs uppercase tracking-[0.18em] text-muted">Quality score</div>
            <div className="mt-2 flex items-baseline gap-3">
              <span className="text-4xl font-bold text-text">{qualityScoreDisplay(site)}</span>
              {!hasScreenshotQA && (
                <span className="text-sm text-amber-400">Estimated — screenshot QA pending</span>
              )}
            </div>
            <div className="mt-3 h-2 w-64 max-w-full overflow-hidden rounded-full bg-white/10">
              <div
                className={`h-full transition-all ${score >= 90 ? "bg-emerald-500" : score >= 75 ? "bg-yellow-500" : score >= 55 ? "bg-orange-500" : "bg-rose-500"}`}
                style={{ width: `${Math.min(score, 100)}%` }}
              />
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge className={qualityBadgeClass(score)}>{qualityLabel(score)} quality</Badge>
            <Badge className={readinessBadgeClass(site.readinessStatus)}>
              {site.readinessStatus.replace(/_/g, " ")}
            </Badge>
            <Badge className={qaBadgeClass(site.qaStatus)}>{site.qaStatus}</Badge>
          </div>
        </div>

        <div className="mt-4 space-y-2 text-sm">
          {checks.slice(0, 6).map((check) => (
            <div key={check.key} className="flex items-start gap-2">
              <span className={check.status === "pass" ? "text-emerald-400" : check.status === "warn" ? "text-amber-400" : "text-rose-400"}>
                {check.status === "pass" ? "✓" : check.status === "warn" ? "⚠" : "✗"}
              </span>
              <span className="text-text">{check.label}</span>
              {check.notes ? <span className="text-muted">— {check.notes}</span> : null}
            </div>
          ))}
          {checks.length > 6 && (
            <div className="text-xs text-muted">+{checks.length - 6} more checks</div>
          )}
        </div>
      </div>

      {/* Theme / palette / hero */}
      <div className="grid gap-3 md:grid-cols-3">
        <div className="rounded-2xl border border-line bg-panel-2 p-4">
          <div className="text-xs uppercase tracking-[0.18em] text-muted">Theme</div>
          <div className="mt-2 font-medium text-text">{site.themeName || "—"}</div>
          <div className="mt-1 text-xs text-muted">{site.themeKey || "—"}</div>
          {site.themeRationale ? <div className="mt-2 text-xs text-muted">{site.themeRationale}</div> : null}
        </div>
        <div className="rounded-2xl border border-line bg-panel-2 p-4">
          <div className="text-xs uppercase tracking-[0.18em] text-muted">Palette</div>
          <div className="mt-2 flex flex-wrap gap-2">
            <Badge className={paletteClass(site.paletteMode)}>{site.paletteMode}</Badge>
          </div>
          {site.paletteRationale ? <div className="mt-2 text-xs text-muted">{site.paletteRationale}</div> : null}
        </div>
        <div className="rounded-2xl border border-line bg-panel-2 p-4">
          <div className="text-xs uppercase tracking-[0.18em] text-muted">Hero variant</div>
          <div className="mt-2 text-sm font-medium text-text">{site.heroVariant.layout}</div>
          <div className="mt-1 text-xs text-muted">{site.heroVariant.visualTreatment}</div>
        </div>
      </div>

      {/* Quality summary */}
      <div className="grid gap-3 sm:grid-cols-3">
        <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/5 px-4 py-3">
          <div className="text-2xl font-semibold text-emerald-300">{summary.passes}</div>
          <div className="text-xs text-muted">Passing checks</div>
        </div>
        <div className="rounded-2xl border border-amber-500/20 bg-amber-500/5 px-4 py-3">
          <div className="text-2xl font-semibold text-amber-300">{summary.warnings}</div>
          <div className="text-xs text-muted">Warnings</div>
        </div>
        <div className="rounded-2xl border border-rose-500/20 bg-rose-500/5 px-4 py-3">
          <div className="text-2xl font-semibold text-rose-300">{summary.failures}</div>
          <div className="text-xs text-muted">Failures</div>
        </div>
      </div>

      {/* Missing requirements */}
      {site.missingRequirements.length > 0 && (
        <div className="rounded-2xl border border-line bg-panel-2 p-4">
          <div className="flex items-center gap-2 text-xs uppercase tracking-[0.18em] text-muted">
            <ShieldAlert className="h-3.5 w-3.5" />
            Missing requirements
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {site.missingRequirements.map((item) => (
              <Badge key={item} className="border-amber-500/40 bg-amber-500/10 text-amber-100">
                {item}
              </Badge>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function SectionsTab({ site }: { site: GeneratedSite }) {
  return (
    <div className="space-y-3">
      {site.sectionStack.length ? (
        <div className="overflow-hidden rounded-2xl border border-line">
          <div className="grid grid-cols-[2fr_1.5fr_2fr_1fr] gap-3 border-b border-line bg-panel-2 px-4 py-3 text-xs uppercase tracking-[0.16em] text-muted">
            <div>Section</div>
            <div>Component</div>
            <div>Title</div>
            <div>Source</div>
          </div>
          <div className="divide-y divide-line">
            {site.sectionStack.map((section: SiteSection, idx: number) => (
              <div key={idx} className="grid grid-cols-[2fr_1.5fr_2fr_1fr] gap-3 px-4 py-3 text-sm hover:bg-white/2">
                <div className="font-medium text-text">{section.kind}</div>
                <div className="text-muted">{section.componentId ?? "—"}</div>
                <div className="text-text">{section.title}</div>
                <div>
                  <Badge
                    className={
                      section.evidence.sourceKind === "source_backed"
                        ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-100"
                        : "border-sky-500/40 bg-sky-500/10 text-sky-100"
                    }
                  >
                    {section.evidence.inferenceLabel}
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="rounded-2xl border border-dashed border-line p-6 text-center text-sm text-muted">
          No sections generated yet.
        </div>
      )}
    </div>
  );
}

function BriefTabContent({
  brief,
  leadId,
}: {
  brief: Awaited<ReturnType<typeof import("@/lib/api/leads").getLeadMasterBrief>>;
  leadId: string;
}) {
  if (!brief) {
    return (
      <div className="rounded-2xl border border-dashed border-line p-6 text-center text-sm text-muted">
        No approved brief found.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Badge
            className={
              brief.approvalState === "approved"
                ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-100"
                : "border-amber-500/40 bg-amber-500/10 text-amber-100"
            }
          >
            {brief.approvalState}
          </Badge>
          <span className="text-xs text-muted">v{brief.version}</span>
        </div>
        <Link href={`/app/leads/${leadId}`} className="text-xs text-accent hover:underline">
          ← Back to lead
        </Link>
      </div>

      {(
        [
          ["Business Goal", brief.businessGoal],
          ["Primary Audience", brief.primaryAudience],
          ["Value Proposition", brief.valueProposition],
          ["Tone & Voice", brief.toneAndVoice],
          ["Visual Style", brief.visualStyle],
          ["Color Strategy", brief.colorStrategy],
        ] as Array<[string, string | undefined]>
      ).map(([label, value]) =>
        value ? (
          <div key={label} className="rounded-2xl border border-line bg-panel-2 p-4">
            <div className="text-xs uppercase tracking-[0.18em] text-muted">{label}</div>
            <div className="mt-2 text-sm text-text">{value}</div>
          </div>
        ) : null
      )}

      {brief.sections.length > 0 && (
        <div className="rounded-2xl border border-line bg-panel-2 p-4">
          <div className="text-xs uppercase tracking-[0.18em] text-muted">Sections</div>
          <div className="mt-3 space-y-2">
            {brief.sections.map((section, idx) => (
              <div key={idx} className="flex items-start gap-2 text-sm">
                <Badge className="mt-0.5 shrink-0 border-white/10 bg-white/5 text-text">
                  {section.headline}
                </Badge>
                <span className="text-muted">{section.purpose}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function SourcesTab({
  extraction,
  site,
}: {
  extraction: Awaited<ReturnType<typeof import("@/lib/api/leads").getLeadExtraction>>;
  site: GeneratedSite;
}) {
  return (
    <div className="space-y-4">
      {/* Pages crawled */}
      {extraction ? (
        <details className="group">
          <summary className="flex cursor-pointer items-center gap-2 rounded-2xl border border-line bg-panel-2 px-4 py-3 text-sm text-text hover:bg-white/5">
            <span className="font-medium">Pages crawled</span>
            <Badge className="ml-auto border-white/10 bg-white/5 text-text">
              {extraction.pagesCrawled}
            </Badge>
          </summary>
          <div className="mt-2 space-y-2 pl-2">
            {extraction.pageInventory.slice(0, 20).map((page) => (
              <div
                key={page.url}
                className="rounded-xl border border-line bg-panel-2 px-3 py-2 text-sm"
              >
                <div className="flex items-center gap-2">
                  <Badge
                    className={
                      page.status === "crawled"
                        ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-100"
                        : "border-amber-500/40 bg-amber-500/10 text-amber-100"
                    }
                  >
                    {page.status}
                  </Badge>
                  <span className="break-all text-muted">{page.url}</span>
                  <Badge className="ml-auto shrink-0 border-white/10 bg-white/5 text-text">
                    {page.confidence}%
                  </Badge>
                </div>
                {page.summary ? (
                  <div className="mt-1 text-xs text-muted">{page.summary}</div>
                ) : null}
              </div>
            ))}
          </div>
        </details>
      ) : (
        <div className="rounded-2xl border border-dashed border-line p-4 text-sm text-muted">
          No extraction data.
        </div>
      )}

      {/* Brand cues */}
      {extraction && extraction.brandAssetCues.length > 0 && (
        <details className="group">
          <summary className="flex cursor-pointer items-center gap-2 rounded-2xl border border-line bg-panel-2 px-4 py-3 text-sm text-text hover:bg-white/5">
            <span className="font-medium">Brand cues</span>
            <Badge className="ml-auto border-white/10 bg-white/5 text-text">
              {extraction.brandAssetCues.length}
            </Badge>
          </summary>
          <div className="mt-2 grid gap-2 pl-2 md:grid-cols-2">
            {extraction.brandAssetCues.map((cue, idx) => (
              <div key={idx} className="rounded-xl border border-line bg-panel-2 px-3 py-2 text-sm">
                <div className="flex items-center gap-2">
                  <Badge className="border-white/10 bg-white/5 text-text">{cue.assetType}</Badge>
                  <span className="font-medium text-text">{cue.label}</span>
                  <Badge className="ml-auto shrink-0 border-white/10 bg-white/5 text-text">
                    {cue.confidence}%
                  </Badge>
                </div>
                <div className="mt-1 text-xs text-muted">{cue.value}</div>
              </div>
            ))}
          </div>
        </details>
      )}

      {/* Extraction gaps */}
      {extraction && extraction.gapItems.length > 0 && (
        <details className="group">
          <summary className="flex cursor-pointer items-center gap-2 rounded-2xl border border-line bg-panel-2 px-4 py-3 text-sm text-text hover:bg-white/5">
            <span className="font-medium">Extraction gaps</span>
            <Badge className="ml-auto border-amber-500/40 bg-amber-500/10 text-amber-100">
              {extraction.gapItems.length}
            </Badge>
          </summary>
          <div className="mt-2 space-y-2 pl-2">
            {extraction.gapItems.map((gap, idx) => (
              <div
                key={idx}
                className="rounded-xl border border-amber-500/20 bg-amber-500/5 px-3 py-2 text-sm text-amber-200"
              >
                {gap}
              </div>
            ))}
          </div>
        </details>
      )}

      {/* Raw source citations */}
      {site.sourceTraceability.length > 0 && (
        <details className="group">
          <summary className="flex cursor-pointer items-center gap-2 rounded-2xl border border-line bg-panel-2 px-4 py-3 text-sm text-text hover:bg-white/5">
            <span className="font-medium">Site citations</span>
            <Badge className="ml-auto border-white/10 bg-white/5 text-text">
              {site.sourceTraceability.length}
            </Badge>
          </summary>
          <div className="mt-2 space-y-2 pl-2">
            {site.sourceTraceability.map((ref: BriefSourceReference, idx: number) => (
              <div key={idx} className="rounded-xl border border-line bg-panel-2 px-3 py-2 text-sm">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge className="border-white/10 bg-white/5 text-text">{ref.kind}</Badge>
                  {ref.evidenceType ? <Badge className="border-white/10 bg-white/5 text-text">{ref.evidenceType}</Badge> : null}
                  <Badge className="border-white/10 bg-white/5 text-text">{ref.confidence}%</Badge>
                  <span className="text-text">{ref.label}</span>
                </div>
                <div className="mt-1 break-all text-xs text-muted">{ref.sourceUrl}</div>
                {ref.excerpt ? <div className="mt-1 text-sm text-text">{ref.excerpt}</div> : null}
              </div>
            ))}
          </div>
        </details>
      )}
    </div>
  );
}

function HistoryTab({
  site,
  versions,
  exportHistory,
}: {
  site: GeneratedSite;
  versions: GeneratedSiteVersion[];
  exportHistory: Awaited<ReturnType<typeof getSiteExportHistory>>;
}) {
  return (
    <div className="space-y-4">
      <div className="space-y-3">
        <div className="text-xs uppercase tracking-[0.18em] text-muted">Generation versions</div>
        {versions.length ? (
          versions.map((version: GeneratedSiteVersion) => (
            <div
              key={version.id}
              className={`rounded-2xl border p-4 ${version.version === site.version ? "border-accent bg-accent/5" : "border-line bg-panel-2"}`}
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <div className="font-medium text-text">
                    Version {version.version}
                    {version.version === site.version ? (
                      <Badge className="ml-2 border-accent/40 bg-accent/10 text-accent text-xs">current</Badge>
                    ) : null}
                  </div>
                  <div className="text-xs text-muted">
                    Generated {formatDateTime(version.createdAt)}
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Badge className={qualityBadgeClass(version.qualityScore)}>
                    {version.qualityScore} / 100
                  </Badge>
                  <Badge className={readinessBadgeClass(version.readinessStatus)}>
                    {version.readinessStatus.replace(/_/g, " ")}
                  </Badge>
                </div>
              </div>
              <div className="mt-3 grid gap-2 text-xs text-muted md:grid-cols-2">
                <div>Theme: {version.themeName}</div>
                <div>Palette: {version.paletteMode}</div>
                <div>Job: {version.generationJobId || "Not recorded"}</div>
                <div className="break-all">Preview: {version.previewUrl}</div>
              </div>
            </div>
          ))
        ) : (
          <div className="text-sm text-muted">
            No version history yet. Generate the first preview to start the trail.
          </div>
        )}
      </div>

      {exportHistory.length > 0 && (
        <div className="space-y-3">
          <div className="text-xs uppercase tracking-[0.18em] text-muted">Export history</div>
          {exportHistory.map((record) => (
            <div key={record.id} className="rounded-2xl border border-line bg-panel-2 p-4 text-sm">
              <div className="flex items-center justify-between gap-3">
                <Badge className="border-white/10 bg-white/5 text-text">{record.exportType}</Badge>
                <Badge
                  className={
                    record.exportSyncStatus === "synced"
                      ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-100"
                      : "border-amber-500/40 bg-amber-500/10 text-amber-100"
                  }
                >
                  {record.exportSyncStatus}
                </Badge>
              </div>
              {record.repoUrl ? (
                <div className="mt-2 break-all text-xs text-muted">{record.repoUrl}</div>
              ) : null}
              <div className="mt-2 text-xs text-muted">
                {formatDateTime(record.createdAt)}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────

export default async function SiteDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const [lead, extraction, brief, site, compare, versions, themes] = await Promise.all([
    getLead(id),
    getLeadExtraction(id),
    getLeadMasterBrief(id),
    getSite(id),
    getSiteCompare(id),
    getSiteVersions(id),
    getThemes(),
  ]);
  const exportHistory = site ? await getSiteExportHistory(id) : [];

  if (!lead) {
    return (
      <PageFrame
        eyebrow="Site workspace"
        title={`Site workspace: ${id}`}
        description="No lead record was found for this identifier."
      >
        <EmptyState
          title="Site source not found"
          description="The workspace needs a lead record before the generator can build a preview site."
          action={
            <Button>
              <Link href="/app/leads">Back to leads</Link>
            </Button>
          }
        />
      </PageFrame>
    );
  }

  const qualityChecks = site?.reviewRubric ?? compare?.reviewRubric ?? [];
  const versionItems = versions?.items ?? [];
  const themeItems = themes.items;
  const hasApprovedBrief = brief?.approvalState === "approved";
  const hasExtraction = Boolean(extraction && extraction.version > 0);
  const previewUrl = site?.previewUrl || `/st/${site?.previewSlug || id}`;
  const score = site?.qualityScore ?? 0;
  const hasScreenshotQA = Boolean(site?.screenshotRefs && site.screenshotRefs.length > 0);

  return (
    <PageFrame
      eyebrow="Site workspace"
      title={lead.companyName || "Site workspace"}
      description="Generated preview, QA state, version history, and source traceability."
    >
      {/* Header bar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          {site ? (
            <>
              <Badge className={qualityBadgeClass(score)}>
                {qualityScoreDisplay(site)} — {qualityLabel(score)}
              </Badge>
              <Badge className={readinessBadgeClass(site.readinessStatus)}>
                {site.readinessStatus.replace(/_/g, " ")}
              </Badge>
              <Badge className={qaBadgeClass(site.qaStatus)}>{site.qaStatus}</Badge>
              {!hasScreenshotQA && (
                <span className="text-xs text-amber-400">screenshot QA pending</span>
              )}
            </>
          ) : (
            <Badge className="border-white/10 bg-white/5 text-muted">Not generated</Badge>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary">
            <Link href={`/compare/${lead.id}`} target="_blank" className="flex items-center gap-1.5">
              Compare all
              <ExternalLink className="h-3.5 w-3.5" />
            </Link>
          </Button>
          <Button variant="secondary">
            <Link href={previewUrl} target="_blank" className="flex items-center gap-1.5">
              Preview site
              <ExternalLink className="h-3.5 w-3.5" />
            </Link>
          </Button>
          <Button variant="secondary">
            <Link href={`/app/leads/${lead.id}`}>← Lead</Link>
          </Button>
        </div>
      </div>

      {/* Main area: left (actions) + right (tabbed content) */}
      <div className="grid gap-4 xl:grid-cols-[0.85fr_1.15fr]">
        {/* Left: generation controls */}
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Generation actions</CardTitle>
              <CardDescription>
                Generate, regenerate, and republish from the approved brief.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <SiteWorkspaceControls
                siteId={id}
                site={site}
                hasApprovedBrief={hasApprovedBrief}
                hasExtraction={hasExtraction}
              />
            </CardContent>
          </Card>

          {site ? (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Sparkles className="h-4 w-4" />
                  Operator refinement
                </CardTitle>
                <CardDescription>
                  Improve the preview with natural-language guidance.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <RefinementPromptInput siteId={id} />
                <PromptHistory
                  prompts={site.promptHistory || []}
                  currentPromptId={site.refinementPromptId}
                />
              </CardContent>
            </Card>
          ) : null}

          {site ? (
            <Card>
              <CardHeader>
                <CardTitle>Source status</CardTitle>
                <CardDescription>Brief and extraction must be ready before generating.</CardDescription>
              </CardHeader>
              <CardContent className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-2xl border border-line bg-panel-2 p-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-muted">Brief</div>
                  <div className="mt-2 text-sm text-text">
                    {brief?.approvalState || "No brief yet"}
                  </div>
                  <div className="mt-1 text-xs text-muted">v{brief?.version ?? 0}</div>
                </div>
                <div className="rounded-2xl border border-line bg-panel-2 p-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-muted">Extraction</div>
                  <div className="mt-2 text-sm text-text">
                    {extraction?.crawlStatus || "idle"}
                  </div>
                  <div className="mt-1 text-xs text-muted">
                    {extraction?.pagesCrawled ?? 0} pages crawled
                  </div>
                </div>
              </CardContent>
            </Card>
          ) : null}

          {site ? (
            <Card>
              <CardHeader>
                <CardTitle>Export & handoff</CardTitle>
                <CardDescription>
                  Download a static bundle or record the handoff destination.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <SiteExportControls
                  siteId={id}
                  previewSlug={site.previewSlug}
                  exportMetadata={site.exportMetadata}
                  history={exportHistory}
                />
              </CardContent>
            </Card>
          ) : null}

          {site && site.overrideDiffs.length > 0 ? (
            <Card>
              <CardHeader>
                <CardTitle>Active overrides</CardTitle>
                <CardDescription>Structured overrides that survive regeneration.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {site.overrideDiffs.map((diff) => (
                  <div key={diff.overrideId} className="rounded-2xl border border-line bg-panel-2 p-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <OverrideDiffBadgeWrapper
                        diff={diff}
                        siteId={id}
                        onDisable={(overrideId) => disableOverrideAction(id, overrideId)}
                      />
                      <Badge className="border-white/10 bg-white/5 text-text">{diff.scope}</Badge>
                      <span className="text-xs text-muted">{diff.path}</span>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          ) : null}
        </div>

        {/* Right: tabbed workspace */}
        {site ? (
          <div>
            <Tabs defaultValue="overview">
              <TabsList variant="line" className="mb-4 flex gap-1">
                <TabsTrigger value="overview">Overview</TabsTrigger>
                <TabsTrigger value="sections">Sections</TabsTrigger>
                <TabsTrigger value="brief">Brief</TabsTrigger>
                <TabsTrigger value="sources">Sources</TabsTrigger>
                <TabsTrigger value="history">History</TabsTrigger>
              </TabsList>

              <TabsContent value="overview">
                <OverviewTab site={site} />
              </TabsContent>

              <TabsContent value="sections">
                <SectionsTab site={site} />
              </TabsContent>

              <TabsContent value="brief">
                <BriefTabContent brief={brief} leadId={lead.id} />
              </TabsContent>

              <TabsContent value="sources">
                <SourcesTab extraction={extraction} site={site} />
              </TabsContent>

              <TabsContent value="history">
                <HistoryTab
                  site={site}
                  versions={versionItems}
                  exportHistory={exportHistory}
                />
              </TabsContent>
            </Tabs>
          </div>
        ) : (
          <div className="space-y-4">
            <EmptyState
              title="Preview not generated yet"
              description="The approved brief exists, but no generated site has been created for this lead yet."
            />

            {/* Theme library — still useful pre-generation */}
            <Card>
              <CardHeader>
                <CardTitle>Theme library</CardTitle>
                <CardDescription>
                  Apply a theme override before or after generation.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {themeItems.length ? (
                  themeItems.map((theme) => (
                    <div
                      key={theme.id}
                      className={`rounded-2xl border p-4 ${themeCardTone(theme)}`}
                    >
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                          <div className="font-medium text-text">{theme.name}</div>
                          <div className="text-xs text-muted">{theme.themeKey}</div>
                        </div>
                        <Badge>{theme.allowedPaletteModes.join(", ")}</Badge>
                      </div>
                      <div className="mt-2 text-sm text-text">{theme.description}</div>
                      <ApplyThemeButton
                        siteId={id}
                        themeKey={theme.themeKey}
                        themeName={theme.name}
                      />
                    </div>
                  ))
                ) : (
                  <div className="text-sm text-muted">Theme library unavailable.</div>
                )}
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </PageFrame>
  );
}
