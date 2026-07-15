import Link from "next/link";
import { ExternalLink, Palette, ShieldAlert, Sparkles } from "lucide-react";

import { EmptyState } from "@/components/state/empty-state";
import { PageFrame } from "@/components/shell/page-frame";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { SiteWorkspaceControls } from "@/components/site-workspace-controls";
import { SiteExportControls } from "@/components/site-export-controls";
import { ApplyThemeButton } from "@/components/apply-theme-button";
import { OverrideDiffBadge } from "@/components/override-diff-badge";
import { RefinementPromptInput } from "@/components/refinement-prompt-input";
import { PromptHistory } from "@/components/prompt-history";
import { ExportSyncModal } from "@/components/export-sync-modal";
import { getLead, getLeadBrief, getLeadExtraction } from "@/lib/api/leads";
import { getSite, getSiteCompare, getSiteVersions, getThemes, getSiteExportHistory, disableSiteOverride } from "@/lib/api/sites";
import type { GeneratedSiteVersion, SiteQualityCheck, ThemeVariant, OverrideDiff, SiteOverrideRecord } from "@/lib/types";

function qualityLabel(score: number) {
  if (score >= 85) return "Excellent";
  if (score >= 70) return "Strong";
  if (score >= 55) return "Review";
  return "Blocked";
}

function qualityBadgeClass(score: number) {
  if (score >= 85) return "border-emerald-500/40 bg-emerald-500/10 text-emerald-100";
  if (score >= 70) return "border-sky-500/40 bg-sky-500/10 text-sky-100";
  if (score >= 55) return "border-amber-500/40 bg-amber-500/10 text-amber-100";
  return "border-rose-500/40 bg-rose-500/10 text-rose-100";
}

function readinessBadgeClass(status: string) {
  if (status === "ready_to_publish" || status === "published") return "border-emerald-500/40 bg-emerald-500/10 text-emerald-100";
  if (status === "ready_for_review") return "border-sky-500/40 bg-sky-500/10 text-sky-100";
  if (status === "needs_review") return "border-amber-500/40 bg-amber-500/10 text-amber-100";
  return "border-rose-500/40 bg-rose-500/10 text-rose-100";
}

function qaBadgeClass(status: string) {
  if (status === "pass") return "border-emerald-500/40 bg-emerald-500/10 text-emerald-100";
  if (status === "warn") return "border-amber-500/40 bg-amber-500/10 text-amber-100";
  return "border-rose-500/40 bg-rose-500/10 text-rose-100";
}

function formatDateTime(value: string | null | undefined) {
  return value ? new Date(value).toLocaleString() : "Not recorded";
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

function summarizeChecks(checks: SiteQualityCheck[]) {
  const failures = checks.filter((check) => check.status === "fail").length;
  const warnings = checks.filter((check) => check.status === "warn").length;
  const passes = checks.filter((check) => check.status === "pass").length;
  return { failures, warnings, passes };
}

function findDiffByPath(diffs: OverrideDiff[], path: string): OverrideDiff | undefined {
  return diffs.find((diff) => diff.path === path);
}

function sectionPreview(section: { title: string; body: string; items: string[]; ctaLabel: string | null; evidence: { inferenceLabel: string; sourceKind: string } }) {
  return (
    <div className="rounded-2xl border border-line bg-panel-2 p-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge>{section.title}</Badge>
        <Badge className={section.evidence.sourceKind === "source_backed" ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-100" : "border-sky-500/40 bg-sky-500/10 text-sky-100"}>
          {section.evidence.inferenceLabel}
        </Badge>
      </div>
      <div className="mt-3 text-sm text-text">{section.body}</div>
      {section.items.length ? (
        <div className="mt-3 flex flex-wrap gap-2">
          {section.items.map((item) => (
            <Badge key={item} className="border-white/10 bg-white/5 text-text">
              {item}
            </Badge>
          ))}
        </div>
      ) : null}
      {section.ctaLabel ? <div className="mt-3 text-xs uppercase tracking-[0.2em] text-muted">{section.ctaLabel}</div> : null}
    </div>
  );
}

export default async function SiteDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const [lead, extraction, brief, site, compare, versions, themes] = await Promise.all([
    getLead(id),
    getLeadExtraction(id),
    getLeadBrief(id),
    getSite(id),
    getSiteCompare(id),
    getSiteVersions(id),
    getThemes()
  ]);
  const exportHistory = site ? await getSiteExportHistory(id) : [];

  if (!lead) {
    return (
      <PageFrame
        eyebrow="Generated site"
        title={`Site workspace: ${id}`}
        description="No lead record was found for this identifier. Create or import a lead first, then generate a preview from the approved brief."
      >
        <EmptyState
          title="Site source not found"
          description="The workspace needs a lead record before the generator can build a preview site."
          action={
            <Button asChild>
              <Link href="/nsa/leads">Back to leads</Link>
            </Button>
          }
        />
      </PageFrame>
    );
  }

  const sitePreviewUrl = site?.previewUrl || `/sites/${id}`;
  const qualityChecks = site?.reviewRubric ?? compare?.reviewRubric ?? [];
  const qualitySummary = summarizeChecks(qualityChecks);
  const versionItems = versions?.items ?? [];
  const themeItems = themes.items;
  const hasApprovedBrief = brief?.approvalState === "approved";
  const hasExtraction = Boolean(extraction && extraction.version > 0);

  return (
    <PageFrame
      eyebrow="Generated site"
      title={lead.companyName || "Missing company name"}
      description="The generated preview, version history, QA state, and export status are linked directly to the approved brief and generation version."
    >
      <div className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
        <Card>
          <CardHeader>
            <div className="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
              <div>
                <CardTitle>Preview state</CardTitle>
                <CardDescription>
                  This panel shows the current generation version, selected theme, preview slug, and the source-safe rationale behind the layout.
                </CardDescription>
              </div>
              <div className="flex flex-wrap gap-2">
                <Badge className={qualityBadgeClass(site?.qualityScore ?? 0)}>
                  {qualityLabel(site?.qualityScore ?? 0)} quality
                </Badge>
                <Badge className={readinessBadgeClass(site?.readinessStatus ?? "blocked")}>{site?.readinessStatus ?? "not created"}</Badge>
                <Badge className={qaBadgeClass(site?.qaStatus ?? "fail")}>{site?.qaStatus ?? "fail"}</Badge>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 md:grid-cols-2">
              <div className="rounded-2xl border border-line bg-panel-2 p-4">
                <div className="text-xs uppercase tracking-[0.18em] text-muted">Preview URL</div>
                <div className="mt-2 break-all text-sm text-text">{sitePreviewUrl}</div>
                <div className="mt-2 text-xs text-muted">Preview slug: {site?.previewSlug || id}</div>
              </div>
              <div className="rounded-2xl border border-line bg-panel-2 p-4">
                <div className="text-xs uppercase tracking-[0.18em] text-muted">Generation trace</div>
                <div className="mt-2 text-sm text-text">Version {site?.version ?? 0}</div>
                <div className="mt-1 text-xs text-muted">Brief v{site?.briefVersion ?? brief?.version ?? 0}</div>
                <div className="mt-1 text-xs text-muted">Job {site?.generationJobId || "Not generated yet"}</div>
              </div>
            </div>

            <div className="grid gap-3 md:grid-cols-3">
              <div className="rounded-2xl border border-line bg-panel-2 p-4">
                <div className="text-xs uppercase tracking-[0.18em] text-muted">Theme</div>
                <div className="mt-2 text-sm text-text">{site?.themeName || "No theme selected yet"}</div>
                <div className="mt-1 text-xs text-muted">{site?.themeKey || "Waiting for generation"}</div>
                {site ? <div className="mt-2 text-xs text-muted">{site.themeRationale}</div> : null}
              </div>
              <div className="rounded-2xl border border-line bg-panel-2 p-4">
                <div className="text-xs uppercase tracking-[0.18em] text-muted">Palette mode</div>
                <div className="mt-2 flex flex-wrap gap-2">
                  <Badge className={site ? paletteClass(site.paletteMode) : "border-white/10 bg-white/5 text-text"}>{site?.paletteMode || "unset"}</Badge>
                </div>
                <div className="mt-2 text-xs text-muted">{site?.paletteRationale || "No palette has been chosen yet."}</div>
              </div>
              <div className="rounded-2xl border border-line bg-panel-2 p-4">
                <div className="text-xs uppercase tracking-[0.18em] text-muted">Quality checks</div>
                <div className="mt-2 text-sm text-text">{qualitySummary.passes} pass, {qualitySummary.warnings} warn, {qualitySummary.failures} fail</div>
                <div className="mt-1 text-xs text-muted">Rendered preview should be reviewed in-browser before publish.</div>
              </div>
            </div>

            {site ? (
              <div className="space-y-4">
                <div className="grid gap-3 md:grid-cols-2">
                  <div className="rounded-2xl border border-line bg-panel-2 p-4">
                    <div className="flex items-center justify-between">
                      <div className="text-xs uppercase tracking-[0.18em] text-muted">Hero variant</div>
                      {findDiffByPath(site.overrideDiffs, "hero.headline") && (
                        <OverrideDiffBadge diff={findDiffByPath(site.overrideDiffs, "hero.headline")!} />
                      )}
                    </div>
                    <div className="mt-2 text-lg font-semibold text-text">{site.heroVariant.headline}</div>
                    <div className="mt-2 text-sm text-muted">{site.heroVariant.subheadline}</div>
                    <div className="mt-2 text-sm text-text">{site.heroVariant.supportingLine}</div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <Badge>{site.heroVariant.layout}</Badge>
                      <Badge>{site.heroVariant.primaryCta}</Badge>
                      <Badge>{site.heroVariant.secondaryCta}</Badge>
                    </div>
                  </div>
                  <div className="rounded-2xl border border-line bg-panel-2 p-4">
                    <div className="flex items-center justify-between">
                      <div className="text-xs uppercase tracking-[0.18em] text-muted">CTA strategy</div>
                      {findDiffByPath(site.overrideDiffs, "cta.primary.label") && (
                        <OverrideDiffBadge diff={findDiffByPath(site.overrideDiffs, "cta.primary.label")!} />
                      )}
                    </div>
                    <div className="mt-2 space-y-3 text-sm text-text">
                      <div>
                        <div className="text-xs uppercase tracking-[0.18em] text-muted">Primary</div>
                        <div className="mt-1">{site.ctaStrategy.primary.label}</div>
                        <div className="mt-1 text-xs text-muted">{site.ctaStrategy.primary.rationale}</div>
                      </div>
                      <div>
                        <div className="text-xs uppercase tracking-[0.18em] text-muted">Secondary</div>
                        <div className="mt-1">{site.ctaStrategy.secondary.label}</div>
                        <div className="mt-1 text-xs text-muted">{site.ctaStrategy.secondary.rationale}</div>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="rounded-2xl border border-line bg-panel-2 p-4">
                  <div className="flex items-center justify-between">
                    <div className="text-xs uppercase tracking-[0.18em] text-muted">Section stack</div>
                    {site.overrideDiffs.some((d) => d.path.startsWith("sectionStack")) && (
                      <Badge className="border-amber-500/40 bg-amber-500/10 text-amber-100">
                        {site.overrideDiffs.filter((d) => d.path.startsWith("sectionStack")).length} overrides
                      </Badge>
                    )}
                  </div>
                  <div className="mt-3 grid gap-3">
                    {site.sectionStack.map((section) => sectionPreview(section))}
                  </div>
                </div>

                <div className="grid gap-3 md:grid-cols-2">
                  <div className="rounded-2xl border border-line bg-panel-2 p-4">
                    <div className="text-xs uppercase tracking-[0.18em] text-muted">Source traceability</div>
                    <div className="mt-3 space-y-2">
                      {site.sourceTraceability.length ? (
                        site.sourceTraceability.map((reference, index) => (
                          <div key={`${reference.kind}-${reference.sourceUrl}-${index}`} className="rounded-xl border border-line bg-panel px-3 py-2">
                            <div className="flex flex-wrap items-center gap-2">
                              <Badge>{reference.kind}</Badge>
                              {reference.evidenceType ? <Badge>{reference.evidenceType}</Badge> : null}
                              {reference.assetType ? <Badge>{reference.assetType}</Badge> : null}
                              <Badge>{reference.confidence}%</Badge>
                              <span className="text-sm text-text">{reference.label}</span>
                            </div>
                            <div className="mt-2 break-all text-xs text-muted">{reference.sourceUrl}</div>
                            <div className="mt-1 text-sm text-text">{reference.excerpt}</div>
                          </div>
                        ))
                      ) : (
                        <div className="text-sm text-muted">No traceable source references were stored for this preview.</div>
                      )}
                    </div>
                  </div>
                  <div className="rounded-2xl border border-line bg-panel-2 p-4">
                    <div className="text-xs uppercase tracking-[0.18em] text-muted">Missing requirements</div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {site.missingRequirements.length ? (
                        site.missingRequirements.map((item) => <Badge key={item} className="border-amber-500/40 bg-amber-500/10 text-amber-100">{item}</Badge>)
                      ) : (
                        <span className="text-sm text-muted">No blocking gaps were recorded.</span>
                      )}
                    </div>
                    <div className="mt-4 flex items-center gap-3 rounded-2xl border border-line bg-panel px-4 py-3 text-xs text-muted">
                      <ShieldAlert className="h-4 w-4" />
                      <span>Browser-based QA should be run against the live preview URL before publishing.</span>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <EmptyState
                title="Preview not generated yet"
                description="The approved brief exists, but no generated site document has been created for this lead yet."
              />
            )}
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Generation actions</CardTitle>
              <CardDescription>Generate, republish, and save structured overrides from the same source-safe site document.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <SiteWorkspaceControls
                  siteId={id}
                  site={site}
                  hasApprovedBrief={hasApprovedBrief}
                  hasExtraction={hasExtraction}
                />
                <div className="flex flex-wrap gap-3">
                  <Button asChild variant="secondary">
                    <Link href={`/nsa/sites/${id}/brief`}>Open brief review</Link>
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          {site ? (
            <Card>
              <CardHeader>
                <CardTitle>Diversity Score</CardTitle>
                <CardDescription>Uniqueness of theme and palette in the current batch</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-4">
                  <div className="text-3xl font-semibold text-text">{site.diversityScore ?? 50}</div>
                  <div className="flex-1">
                    <div className="h-2 rounded-full bg-white/10 overflow-hidden">
                      <div
                        className="h-full bg-accent transition-all"
                        style={{ width: `${site.diversityScore ?? 50}%` }}
                      />
                    </div>
                  </div>
                </div>
                {(site.diversityScore ?? 50) < 60 && (
                  <div className="mt-2 text-sm text-amber-400">
                    Consider theme variation to improve diversity
                  </div>
                )}
                {site.diversityNotes?.map((note: string) => (
                  <div key={note} className="mt-1 text-xs text-muted">{note}</div>
                ))}
              </CardContent>
            </Card>
          ) : null}

          {site ? (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Sparkles className="h-5 w-5" />
                  Visual QA Analysis
                </CardTitle>
                <CardDescription>Screenshot-based visual quality evaluation and readiness assessment</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-3 md:grid-cols-3">
                  <div className="rounded-2xl border border-line bg-panel-2 p-4">
                    <div className="text-xs uppercase tracking-[0.18em] text-muted">Quality Score</div>
                    <div className="mt-2 text-3xl font-semibold text-text">{site.qualityScore ?? "—"}/100</div>
                    <div className="mt-2 h-2 rounded-full bg-white/10 overflow-hidden">
                      <div
                        className="h-full bg-accent transition-all"
                        style={{ width: `${Math.min(site.qualityScore ?? 0, 100)}%` }}
                      />
                    </div>
                  </div>
                  <div className="rounded-2xl border border-line bg-panel-2 p-4">
                    <div className="text-xs uppercase tracking-[0.18em] text-muted">QA Status</div>
                    <div className="mt-2">
                      {site.qaStatus ? (
                        <Badge className={`${qaBadgeClass(site.qaStatus)} text-sm px-3 py-2`}>
                          {site.qaStatus === "pass" ? "✓ Passed" : site.qaStatus === "warn" ? "⚠ Warning" : "✗ Failed"}
                        </Badge>
                      ) : (
                        <div className="text-sm text-muted">No QA analysis</div>
                      )}
                    </div>
                  </div>
                  <div className="rounded-2xl border border-line bg-panel-2 p-4">
                    <div className="text-xs uppercase tracking-[0.18em] text-muted">Readiness</div>
                    <div className="mt-2">
                      {site.readinessStatus ? (
                        <Badge className={`${readinessBadgeClass(site.readinessStatus)} text-sm px-3 py-2`}>
                          {site.readinessStatus.replace(/_/g, " ")}
                        </Badge>
                      ) : (
                        <div className="text-sm text-muted">Pending</div>
                      )}
                    </div>
                  </div>
                </div>

                {site.screenshotRefs && site.screenshotRefs.length > 0 ? (
                  <div className="rounded-2xl border border-line bg-panel-2 p-4">
                    <div className="text-xs uppercase tracking-[0.18em] text-muted mb-3">Screenshots</div>
                    <div className="space-y-3">
                      {site.screenshotRefs.map((ref, idx) => (
                        <div key={idx} className="rounded-xl border border-line bg-panel p-3">
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-sm font-medium text-text">{ref.label}</span>
                            {ref.capturedAt && (
                              <span className="text-xs text-muted">{formatDateTime(ref.capturedAt)}</span>
                            )}
                          </div>
                          {ref.url && (
                            <a href={ref.url} target="_blank" rel="noopener noreferrer" className="text-xs text-accent hover:underline break-all">
                              View screenshot ↗
                            </a>
                          )}
                          {ref.notes && (
                            <div className="mt-2 text-xs text-muted italic">{ref.notes}</div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}

                {site.improvementRecommendations ? (
                  <div className="rounded-2xl border border-line bg-panel-2 p-4">
                    <div className="flex items-center justify-between mb-2">
                      <div className="text-xs uppercase tracking-[0.18em] text-muted">Auto-improvement brief</div>
                      {site.improvementRecommendations.estimatedNewScore != null && (
                        <span className="text-xs text-muted">
                          Target score: {site.improvementRecommendations.estimatedNewScore}/100
                        </span>
                      )}
                    </div>
                    {site.improvementRecommendations.overallApproach && (
                      <p className="text-sm text-text mb-2">
                        {site.improvementRecommendations.overallApproach}
                      </p>
                    )}
                    {site.improvementRecommendations.sectionImprovements &&
                      site.improvementRecommendations.sectionImprovements.length > 0 && (
                        <div className="mt-2 space-y-2">
                          {site.improvementRecommendations.sectionImprovements.slice(0, 4).map((imp) => (
                            <div key={`${imp.sectionTitle}-${imp.priority}`} className="rounded-xl border border-line bg-panel px-3 py-2">
                              <div className="flex items-center justify-between gap-2">
                                <span className="text-xs font-medium text-text">{imp.sectionTitle}</span>
                                <span className="text-[0.65rem] uppercase tracking-[0.18em] text-muted">{imp.priority}</span>
                              </div>
                              {imp.recommendedChanges && imp.recommendedChanges.length > 0 && (
                                <ul className="mt-1 list-disc pl-4 text-xs text-muted">
                                  {imp.recommendedChanges.slice(0, 3).map((note, idx) => (
                                    <li key={idx}>{note}</li>
                                  ))}
                                </ul>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    {site.improvementRecommendations.implementationNotes && (
                      <div className="mt-2 text-xs text-muted italic">
                        {site.improvementRecommendations.implementationNotes}
                      </div>
                    )}
                  </div>
                ) : null}
              </CardContent>
            </Card>
          ) : null}

          {site ? (
            <Card>
              <CardHeader>
                <CardTitle>Operator Refinement</CardTitle>
                <CardDescription>Iteratively improve the preview with natural-language guidance.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <RefinementPromptInput siteId={id} />
                <PromptHistory prompts={site.promptHistory || []} currentPromptId={site.refinementPromptId} />
              </CardContent>
            </Card>
          ) : null}

          {site ? (
            <Card>
              <CardHeader>
                <CardTitle>Layout Analysis</CardTitle>
                <CardDescription>Hash and duplicate detection metadata</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="text-xs uppercase tracking-[0.18em] text-muted">Layout Hash</div>
                  <div className="font-mono text-sm text-text break-all">{site.layoutHash || "Not computed"}</div>
                </div>
              </CardContent>
            </Card>
          ) : null}

          <Card>
            <CardHeader>
              <CardTitle>Before / after comparison</CardTitle>
              <CardDescription>Source brief fields and generated site decisions sit side by side so changes stay explainable.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {compare?.entries?.length ? (
                compare.entries.map((entry) => (
                  <div key={entry.label} className="rounded-2xl border border-line bg-panel-2 p-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge className={entry.status === "matched" ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-100" : entry.status === "inferred" ? "border-sky-500/40 bg-sky-500/10 text-sky-100" : "border-amber-500/40 bg-amber-500/10 text-amber-100"}>
                        {entry.status}
                      </Badge>
                      <span className="text-sm text-text">{entry.label}</span>
                    </div>
                    <div className="mt-3 grid gap-3 text-sm md:grid-cols-2">
                      <div>
                        <div className="text-xs uppercase tracking-[0.18em] text-muted">Source</div>
                        <div className="mt-1 text-text">{entry.sourceValue}</div>
                      </div>
                      <div>
                        <div className="text-xs uppercase tracking-[0.18em] text-muted">Generated</div>
                        <div className="mt-1 text-text">{entry.generatedValue}</div>
                      </div>
                    </div>
                    <div className="mt-2 text-xs text-muted">{entry.reason}</div>
                  </div>
                ))
              ) : (
                <div className="text-sm text-muted">The comparison payload will appear after the first preview generation.</div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Review rubric</CardTitle>
              <CardDescription>This rubric is meant for browser-based screenshot QA against the live preview URL.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {qualityChecks.length ? (
                qualityChecks.map((check) => (
                  <div key={check.key} className="rounded-2xl border border-line bg-panel-2 p-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge className={qaBadgeClass(check.status)}>{check.status}</Badge>
                      <span className="text-sm text-text">{check.label}</span>
                    </div>
                    <div className="mt-2 text-sm text-text">{check.notes}</div>
                  </div>
                ))
              ) : (
                <div className="text-sm text-muted">No rubric is available until the first preview generation runs.</div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Version history</CardTitle>
              <CardDescription>Each generation is immutable and traceable back to the brief version and job id that produced it.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {versionItems.length ? (
                versionItems.map((version: GeneratedSiteVersion) => (
                  <div key={version.id} className={`rounded-2xl border p-4 ${version.version === site?.version ? "border-accent bg-accent/5" : "border-line bg-panel-2"}`}>
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <div className="font-medium text-text">Version {version.version}</div>
                        <div className="text-xs text-muted">Generated {formatDateTime(version.createdAt)}</div>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <Badge className={qualityBadgeClass(version.qualityScore)}>{version.qualityScore}</Badge>
                        <Badge className={readinessBadgeClass(version.readinessStatus)}>{version.readinessStatus}</Badge>
                      </div>
                    </div>
                    <div className="mt-3 grid gap-2 text-xs text-muted md:grid-cols-2">
                      <div>Theme: {version.themeName}</div>
                      <div>Palette: {version.paletteMode}</div>
                      <div>Job: {version.generationJobId || "Not recorded"}</div>
                      <div>Preview: {version.previewUrl}</div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-sm text-muted">No version history yet. Generate the first preview to create the history trail.</div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Theme library</CardTitle>
              <CardDescription>The selected theme should be explainable from the source site&apos;s visual language and conversion posture.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {site && site.overrides?.some((o) => o.path === "themeKey") ? (
                <div className="mb-3 flex items-center gap-3">
                  <Badge>Operator theme: {site.themeName}</Badge>
                  <Button variant="ghost" disabled>Remove override (future)</Button>
                </div>
              ) : null}
              {themeItems.length ? (
                themeItems.map((theme) => (
                  <div key={theme.id} className={`rounded-2xl border p-4 ${themeCardTone(theme)} ${site?.themeKey === theme.themeKey ? "ring-1 ring-accent" : ""}`}>
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <div className="font-medium text-text">{theme.name}</div>
                        <div className="text-xs text-muted">{theme.themeKey}</div>
                      </div>
                      <Badge>{theme.allowedPaletteModes.join(", ")}</Badge>
                    </div>
                    <div className="mt-2 text-sm text-text">{theme.description}</div>
                    <div className="mt-2 text-xs text-muted">Best for: {theme.bestForIndustries.join(", ")}</div>
                      <ApplyThemeButton siteId={id} themeKey={theme.themeKey} themeName={theme.name} />
                  </div>
                ))
              ) : (
                <div className="text-sm text-muted">Theme library unavailable.</div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Brand tokens</CardTitle>
              <CardDescription>Each token shows whether it is grounded in source cues or inferred from the approved brief.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {site ? (
                <div className="grid gap-3 md:grid-cols-2">
                  {([
                    ["Primary", site.brandTokens.primaryColor, "brandTokens.primaryColor"],
                    ["Secondary", site.brandTokens.secondaryColor, "brandTokens.secondaryColor"],
                    ["Accent", site.brandTokens.accentColor, "brandTokens.accentColor"],
                    ["Typography", site.brandTokens.typography, "brandTokens.typography"],
                    ["Visual tone", site.brandTokens.visualTone, "brandTokens.visualTone"],
                    ["Layout density", site.brandTokens.layoutDensity, "brandTokens.layoutDensity"]
                  ] as Array<[string, { value: string; evidence: { inferenceLabel: string; sourceKind: string } }, string]>).map(([label, token, path]) => (
                    <div key={label} className="rounded-2xl border border-line bg-panel-2 p-4">
                      <div className="flex items-center justify-between">
                        <div className="text-xs uppercase tracking-[0.18em] text-muted">{label}</div>
                        {findDiffByPath(site.overrideDiffs, path) && (
                          <OverrideDiffBadge diff={findDiffByPath(site.overrideDiffs, path)!} />
                        )}
                      </div>
                      <div className="mt-2 text-sm text-text">{token.value}</div>
                      <div className="mt-2 text-xs text-muted">{token.evidence.inferenceLabel}</div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-sm text-muted">Brand tokens will appear after the first generation run.</div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Source status</CardTitle>
              <CardDescription>The preview can only move forward when the brief and crawl are ready.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-3 md:grid-cols-2">
              <div className="rounded-2xl border border-line bg-panel-2 p-4">
                <div className="text-xs uppercase tracking-[0.18em] text-muted">Brief</div>
                <div className="mt-2 text-sm text-text">{brief?.approvalState || "No brief yet"}</div>
                <div className="mt-1 text-xs text-muted">Version {brief?.version ?? 0}</div>
              </div>
              <div className="rounded-2xl border border-line bg-panel-2 p-4">
                <div className="text-xs uppercase tracking-[0.18em] text-muted">Extraction</div>
                <div className="mt-2 text-sm text-text">{extraction?.crawlStatus || "idle"}</div>
                <div className="mt-1 text-xs text-muted">Pages crawled: {extraction?.pagesCrawled ?? 0}</div>
              </div>
            </CardContent>
          </Card>

          {site ? (
            <Card>
              <CardHeader>
                <CardTitle>Export & handoff</CardTitle>
                <CardDescription>Download a static bundle or record the GitHub handoff destination for this preview.</CardDescription>
              </CardHeader>
              <CardContent>
                <SiteExportControls siteId={id} previewSlug={site.previewSlug} exportMetadata={site.exportMetadata} history={exportHistory} />
              </CardContent>
            </Card>
          ) : null}

          {site && site.overrideDiffs.length > 0 ? (
            <Card>
              <CardHeader>
                <CardTitle>Active Overrides</CardTitle>
                <CardDescription>Structured overrides that will survive regeneration.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {site.overrideDiffs.map((diff) => (
                  <div key={diff.overrideId} className="rounded-2xl border border-line bg-panel-2 p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex flex-wrap items-center gap-2">
                        <OverrideDiffBadge diff={diff} onDisable={async (overrideId) => {
                          await disableSiteOverride(id, overrideId);
                          window.location.reload();
                        }} />
                        <Badge className="border-white/10 bg-white/5 text-text">{diff.scope}</Badge>
                      </div>
                    </div>
                    <div className="mt-3 space-y-2 text-sm">
                      <div>
                        <div className="text-xs uppercase tracking-[0.18em] text-muted">Path</div>
                        <div className="mt-1 text-text">{diff.path}</div>
                      </div>
                      {diff.previousValue !== null && (
                        <div>
                          <div className="text-xs uppercase tracking-[0.18em] text-muted">Previous value</div>
                          <div className="mt-1 rounded-xl border border-line/50 bg-panel px-3 py-2 text-muted">
                            {String(diff.previousValue)}
                          </div>
                        </div>
                      )}
                      <div>
                        <div className="text-xs uppercase tracking-[0.18em] text-muted">Current value</div>
                        <div className="mt-1 rounded-xl border border-line/50 bg-panel px-3 py-2 text-text">
                          {String(diff.currentValue)}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          ) : null}

          <Card>
            <CardHeader>
              <CardTitle>Related links</CardTitle>
              <CardDescription>Jump between the source lead, the brief, the preview, and the edit workspace.</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-3">
              <Button asChild>
                <Link href={`/nsa/leads/${lead.id}`}>Back to lead</Link>
              </Button>
              <Button asChild variant="secondary">
                <Link href={`/sites/${site?.previewSlug || id}`} target="_blank">
                  Open preview
                  <ExternalLink className="ml-2 h-4 w-4" />
                </Link>
              </Button>
              <Button asChild variant="secondary">
                <Link href={`/nsa/sites/${id}/edit`}>
                  Edit workspace
                  <Sparkles className="ml-2 h-4 w-4" />
                </Link>
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </PageFrame>
  );
}
