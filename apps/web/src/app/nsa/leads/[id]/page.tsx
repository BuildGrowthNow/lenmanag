import Link from "next/link";
import { Merge } from "lucide-react";

import { PageFrame } from "@/components/shell/page-frame";
import { EmptyState } from "@/components/state/empty-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { LeadBriefReview } from "@/components/lead-brief-review";
import { LeadExtractionControls } from "@/components/lead-extraction-controls";
import { getLead, getLeadBrief, getLeadExtraction, getLeadPages } from "@/lib/api/leads";
import { getSite } from "@/lib/api/sites";
import { evaluateExtractionHealth } from "@/lib/extraction-health";
import type { PageInventoryItem } from "@/lib/types";

function statusLabel(status: string) {
  if (status === "needs_review") return "Needs review";
  return status.charAt(0).toUpperCase() + status.slice(1);
}

function jobLabel(status: string) {
  if (status === "running") return "Running";
  if (status === "queued") return "Queued";
  if (status === "failed") return "Failed";
  return "Completed";
}

function jobBadgeClass(status: string) {
  if (status === "running") return "border-blue-500/40 bg-blue-500/10 text-blue-100";
  if (status === "queued") return "border-sky-500/40 bg-sky-500/10 text-sky-100";
  if (status === "failed") return "border-rose-500/40 bg-rose-500/10 text-rose-100";
  return "border-emerald-500/40 bg-emerald-500/10 text-emerald-100";
}

function extractionBadgeClass(status: string) {
  if (status === "running") return "border-blue-500/40 bg-blue-500/10 text-blue-100";
  if (status === "queued") return "border-sky-500/40 bg-sky-500/10 text-sky-100";
  if (status === "partial") return "border-amber-500/40 bg-amber-500/10 text-amber-100";
  if (status === "failed") return "border-rose-500/40 bg-rose-500/10 text-rose-100";
  return "border-emerald-500/40 bg-emerald-500/10 text-emerald-100";
}

function confidenceBadgeClass(confidence: number) {
  if (confidence >= 75) return "border-emerald-500/40 bg-emerald-500/10 text-emerald-100";
  if (confidence >= 50) return "border-amber-500/40 bg-amber-500/10 text-amber-100";
  return "border-rose-500/40 bg-rose-500/10 text-rose-100";
}

function extractionStatusLabel(status: string) {
  if (status === "idle") return "Not started";
  if (status === "queued") return "Queued";
  if (status === "running") return "Running";
  if (status === "partial") return "Partial";
  if (status === "failed") return "Failed";
  return "Complete";
}

function sitemapStatusLabel(status: string) {
  if (status === "found") return "Found";
  if (status === "missing") return "Missing";
  if (status === "blocked") return "Blocked";
  if (status === "error") return "Error";
  return "Unknown";
}

function pageStatusLabel(status: string) {
  if (status === "crawled") return "Crawled";
  if (status === "failed") return "Failed";
  if (status === "blocked") return "Blocked";
  return "Discovered";
}

function pageSourceLabel(source: string) {
  if (source === "homepage") return "Homepage";
  if (source === "sitemap") return "Sitemap";
  return "Internal link";
}

function confidenceLabel(confidence: number) {
  if (confidence >= 75) return "High";
  if (confidence >= 50) return "Medium";
  return "Low";
}

function formatDateTime(value: string) {
  return new Date(value).toLocaleString();
}

function progressWidth(progress: number) {
  return `${Math.max(0, Math.min(100, progress))}%`;
}

function ProgressBar({ progress, label }: { progress: number; label: string }) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-3 text-xs text-muted">
        <span>{label}</span>
        <span>{progress}%</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-white/8">
        <div className="h-full rounded-full bg-accent" style={{ width: progressWidth(progress) }} />
      </div>
    </div>
  );
}

export default async function LeadDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const [lead, extraction, pages, brief, site] = await Promise.all([getLead(id), getLeadExtraction(id), getLeadPages(id), getLeadBrief(id), getSite(id)]);

  if (!lead) {
    return (
      <PageFrame
        eyebrow="Lead detail"
        title={`Lead workspace: ${id}`}
        description="No lead record was found for this identifier. Import a CSV or create a manual lead first."
      >
        <EmptyState
          title="Lead not found"
          description="The ID does not map to a stored lead record yet. Return to the intake list and create or import a lead."
          action={
            <Link href="/nsa/leads"><Button>Back to leads</Button></Link>
          }
        />
      </PageFrame>
    );
  }

  const extractionSnapshot = extraction;
  const pageInventory = pages?.pages ?? extractionSnapshot?.pageInventory ?? [];
  const topCitations = extractionSnapshot?.sourceCitations.slice(0, 4) ?? [];
  const brandCues = extractionSnapshot?.brandAssetCues ?? [];
  const extractionGapItems = extractionSnapshot?.gapItems ?? [];
  const extractionHealth = evaluateExtractionHealth(extractionSnapshot);

  return (
    <PageFrame
      eyebrow="Lead detail"
      title={lead.companyName || "Missing company name"}
      description="Lead identity stays separate from job history and source provenance so merges remain traceable."
    >
      <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <Card>
          <CardHeader>
            <CardTitle>Lead snapshot</CardTitle>
            <CardDescription>Canonical intake record and merge-safe source details.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            {lead.sourceRefs.length > 1 ? (
              <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-amber-100">
                <div className="flex items-start gap-3">
                  <Merge className="mt-0.5 h-4 w-4 shrink-0" />
                  <div>
                    <div className="font-medium">Merged intake record</div>
                    <div className="mt-1 text-xs leading-5 text-amber-100/80">
                      This lead keeps every source reference attached so duplicate-domain merges stay reviewable instead of disappearing into the canonical record.
                    </div>
                  </div>
                </div>
              </div>
            ) : null}

            <div className="grid gap-3 md:grid-cols-2">
              <div className="rounded-2xl border border-line bg-panel-2 p-4">
                <div className="text-xs uppercase tracking-[0.18em] text-muted">Website</div>
                <div className="mt-2 break-all text-text">{lead.websiteUrl}</div>
                <div className="mt-2 text-xs text-muted">Normalized: {lead.normalizedWebsiteUrl}</div>
              </div>
              <div className="rounded-2xl border border-line bg-panel-2 p-4">
                <div className="text-xs uppercase tracking-[0.18em] text-muted">Status</div>
                <div className="mt-2 flex flex-wrap gap-2">
                  <Badge>{statusLabel(lead.status)}</Badge>
                  <Badge>{lead.sourceType}</Badge>
                  <Badge>v{lead.version}</Badge>
                  {lead.sourceRefs.length > 1 ? (
                    <Badge className="border-amber-500/40 bg-amber-500/10 text-amber-100">
                      <Merge className="mr-1 h-3.5 w-3.5" />
                      {lead.sourceRefs.length} sources
                    </Badge>
                  ) : null}
                </div>
                <div className="mt-2 text-xs text-muted">Updated {new Date(lead.updatedAt).toLocaleString()}</div>
              </div>
            </div>

            {lead.latestJob ? (
              <div className="rounded-2xl border border-line bg-panel-2 p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <div className="text-xs uppercase tracking-[0.18em] text-muted">Latest job</div>
                    <div className="mt-2 font-medium text-text">{lead.latestJob.step}</div>
                    <div className="mt-1 text-xs text-muted">
                      Job {lead.latestJob.id.slice(0, 8)} - {lead.latestJob.jobType}
                    </div>
                  </div>
                  <Badge className={jobBadgeClass(lead.latestJob.status)}>{jobLabel(lead.latestJob.status)}</Badge>
                </div>
                <div className="mt-4">
                  <ProgressBar progress={lead.latestJob.progress} label="Job progress" />
                </div>
                <div className="mt-4 grid gap-2 text-xs text-muted sm:grid-cols-2">
                  <div>Started: {lead.latestJob.startedAt ? formatDateTime(lead.latestJob.startedAt) : "Not recorded"}</div>
                  <div>Finished: {lead.latestJob.finishedAt ? formatDateTime(lead.latestJob.finishedAt) : "Not recorded"}</div>
                </div>
                {lead.latestJob.errorMessage ? <div className="mt-3 text-xs text-rose-100/80">Error: {lead.latestJob.errorMessage}</div> : null}
              </div>
            ) : null}

            <div className="grid gap-3 md:grid-cols-2">
              <div className="rounded-2xl border border-line bg-panel-2 p-4">
                <div className="text-xs uppercase tracking-[0.18em] text-muted">Company</div>
                <div className="mt-2 text-text">{lead.companyName || "Missing company name"}</div>
                <div className="mt-2 text-xs text-muted">Industry: {lead.industry || "Not provided"}</div>
              </div>
              <div className="rounded-2xl border border-line bg-panel-2 p-4">
                <div className="text-xs uppercase tracking-[0.18em] text-muted">Gaps</div>
                <div className="mt-2 flex flex-wrap gap-2">
                  {lead.missingFields.length ? (
                    lead.missingFields.map((field) => <Badge key={field}>{field}</Badge>)
                  ) : (
                    <span className="text-sm text-muted">No missing intake fields.</span>
                  )}
                </div>
              </div>
            </div>

            <div className="rounded-2xl border border-line bg-panel-2 p-4">
              <div className="text-xs uppercase tracking-[0.18em] text-muted">Notes</div>
              <div className="mt-2 whitespace-pre-wrap text-text">{lead.notes || "No notes supplied."}</div>
            </div>

            <div className="rounded-2xl border border-line bg-panel-2 p-4">
              <div className="text-xs uppercase tracking-[0.18em] text-muted">Source references</div>
              <div className="mt-3 space-y-2">
                {lead.sourceRefs.length ? (
                  lead.sourceRefs.map((source, index) => (
                    <div key={`${source.sourceType}-${index}`} className="rounded-xl border border-line bg-panel px-3 py-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge>{source.sourceType}</Badge>
                        <span className="text-sm text-text">{source.sourceRef || "No source ref"}</span>
                      </div>
                      <div className="mt-1 text-xs text-muted">{new Date(source.importedAt).toLocaleString()}</div>
                    </div>
                  ))
                ) : (
                  <div className="text-sm text-muted">No source provenance recorded yet.</div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="space-y-4">
          <LeadBriefReview leadId={lead.id} brief={brief} extractionHealth={extractionHealth} />

          <Card>
            <CardHeader>
              <CardTitle>Generated site</CardTitle>
              <CardDescription>The approved brief feeds the generated preview site, which stays traceable to the lead and generation version.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {site ? (
                <>
                  <div className="grid gap-3 md:grid-cols-2">
                    <div className="rounded-2xl border border-line bg-panel-2 p-4">
                      <div className="text-xs uppercase tracking-[0.18em] text-muted">Preview URL</div>
                      <div className="mt-2 break-all text-text">{site.previewUrl}</div>
                      <div className="mt-1 text-xs text-muted">Slug: {site.previewSlug}</div>
                    </div>
                    <div className="rounded-2xl border border-line bg-panel-2 p-4">
                      <div className="text-xs uppercase tracking-[0.18em] text-muted">Readiness</div>
                      <div className="mt-2 text-text">{site.readinessStatus}</div>
                      <div className="mt-1 text-xs text-muted">Quality score: {site.qualityScore}</div>
                    </div>
                  </div>
                  <div className="grid gap-3 md:grid-cols-2">
                    <div className="rounded-2xl border border-line bg-panel-2 p-4">
                      <div className="text-xs uppercase tracking-[0.18em] text-muted">Theme</div>
                      <div className="mt-2 text-text">{site.themeName}</div>
                      <div className="mt-1 text-xs text-muted">{site.themeRationale}</div>
                    </div>
                    <div className="rounded-2xl border border-line bg-panel-2 p-4">
                      <div className="text-xs uppercase tracking-[0.18em] text-muted">Palette</div>
                      <div className="mt-2 text-text">{site.paletteMode}</div>
                      <div className="mt-1 text-xs text-muted">{site.paletteRationale}</div>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-3">
                    <Button>
                      <Link href={`/nsa/sites/${lead.id}`}>Open site workspace</Link>
                    </Button>
                    <Button variant="secondary">
                      <Link href={`/sites/${site.previewSlug}`}>Open preview</Link>
                    </Button>
                  </div>
                </>
              ) : (
                <EmptyState
                  title="Preview not generated yet"
                  description="Approve the brief, then generate the preview site from the generated-site workspace."
                  action={
                    <Button>
                      <Link href={`/nsa/sites/${lead.id}`}>Go to site workspace</Link>
                    </Button>
                  }
                />
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <CardTitle>Extraction review</CardTitle>
                  <CardDescription>Public website signals, crawl status, and missing-data gaps stay visible here so operators can trace the brief back to source material.</CardDescription>
                </div>
                <Button variant="secondary">
                  <Link href={`/nsa/leads/${lead.id}/extraction`}>View page inventory</Link>
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <LeadExtractionControls leadId={lead.id} extraction={extractionSnapshot} />

              <div className="grid gap-3 md:grid-cols-2">
                <div className="rounded-2xl border border-line bg-panel-2 p-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-muted">Crawl status</div>
                  <div className="mt-2 flex flex-wrap gap-2">
                    <Badge className={extractionBadgeClass(extractionSnapshot?.crawlStatus || "idle")}>
                      {extractionStatusLabel(extractionSnapshot?.crawlStatus || "idle")}
                    </Badge>
                    <Badge>{sitemapStatusLabel(extractionSnapshot?.sitemapStatus || "unknown")} sitemap</Badge>
                    <Badge>{confidenceLabel(extractionSnapshot?.confidenceScore || 0)} confidence</Badge>
                  </div>
                  <div className="mt-3 grid gap-2 text-xs text-muted">
                    <div>Detected website: {extractionSnapshot?.detectedWebsiteUrl || "No redirected website detected yet."}</div>
                    <div>Pages discovered: {extractionSnapshot?.pagesDiscovered ?? 0}</div>
                    <div>Pages crawled: {extractionSnapshot?.pagesCrawled ?? 0}</div>
                    <div>Source citations: {extractionSnapshot?.sourceCitations.length ?? 0}</div>
                  </div>
                </div>
                <div className="rounded-2xl border border-line bg-panel-2 p-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-muted">Extraction summary</div>
                  <div className="mt-2 text-sm text-text">{extractionSnapshot?.summary.positioningSummary || "No positioning summary yet."}</div>
                  <div className="mt-3 text-xs text-muted">Company: {extractionSnapshot?.summary.companyName || lead.companyName || "Not provided"}</div>
                  <div className="mt-2 text-xs text-muted">Canonical URL: {extractionSnapshot?.summary.canonicalWebsiteUrl || lead.websiteUrl}</div>
                  <div className="mt-3 space-y-2 text-xs text-muted">
                    <div className="flex flex-wrap gap-2">
                      {extractionSnapshot?.summary.audienceClues.length ? (
                        extractionSnapshot.summary.audienceClues.map((clue) => <Badge key={clue}>{clue}</Badge>)
                      ) : (
                        <span>No audience clue yet.</span>
                      )}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {extractionSnapshot?.summary.serviceClues.length ? (
                        extractionSnapshot.summary.serviceClues.map((clue) => <Badge key={clue}>{clue}</Badge>)
                      ) : (
                        <span>No service clue yet.</span>
                      )}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {extractionSnapshot?.summary.ctaClues.length ? (
                        extractionSnapshot.summary.ctaClues.map((clue) => <Badge key={clue}>{clue}</Badge>)
                      ) : (
                        <span>No CTA clue yet.</span>
                      )}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {extractionSnapshot?.summary.toneClues.length ? (
                        extractionSnapshot.summary.toneClues.map((clue) => <Badge key={clue}>{clue}</Badge>)
                      ) : (
                        <span>No tone cue yet.</span>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                <div className="rounded-2xl border border-line bg-panel-2 p-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-muted">Brand cues</div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {brandCues.length ? (
                      brandCues.map((cue, index) => (
                        <Badge key={`${cue.assetType}-${index}`} className={confidenceBadgeClass(cue.confidence)}>
                          {cue.assetType}: {cue.label}
                        </Badge>
                      ))
                    ) : (
                      <span className="text-sm text-muted">No brand assets captured yet.</span>
                    )}
                  </div>
                  {brandCues.length ? (
                    <div className="mt-3 space-y-2 text-xs text-muted">
                      {brandCues.map((cue, index) => (
                        <div key={`${cue.assetType}-${index}`} className="rounded-xl border border-line bg-panel px-3 py-2">
                          <div className="flex flex-wrap items-center gap-2">
                            <Badge>{cue.assetType}</Badge>
                            <span className="text-text">{cue.value}</span>
                            <Badge className={confidenceBadgeClass(cue.confidence)}>{cue.confidence}%</Badge>
                          </div>
                          <div className="mt-1">Source: {cue.sourceUrl}</div>
                          {cue.note ? <div className="mt-1">{cue.note}</div> : null}
                        </div>
                      ))}
                    </div>
                  ) : null}
                </div>
                <div className="rounded-2xl border border-line bg-panel-2 p-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-muted">Gaps</div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {extractionGapItems.length ? (
                      extractionGapItems.map((gap) => <Badge key={gap}>{gap}</Badge>)
                    ) : (
                      <span className="text-sm text-muted">No extraction gaps recorded.</span>
                    )}
                  </div>
                  <div className="mt-3 space-y-2 text-xs text-muted">
                    {pages?.errors?.length ? (
                      pages.errors.map((error) => (
                        <div key={error} className="rounded-xl border border-line bg-panel px-3 py-2 text-rose-100/80">
                          {error}
                        </div>
                      ))
                    ) : null}
                  </div>
                </div>
              </div>

              <div className="rounded-2xl border border-line bg-panel-2 p-4">
                <div className="text-xs uppercase tracking-[0.18em] text-muted">Source citations</div>
                <div className="mt-3 space-y-2">
                  {topCitations.length ? (
                    topCitations.map((citation, index) => (
                      <div key={`${citation.pageUrl}-${index}`} className="rounded-xl border border-line bg-panel px-3 py-2">
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge>{citation.evidenceType}</Badge>
                          <Badge className={confidenceBadgeClass(citation.confidence)}>{citation.confidence}%</Badge>
                          <span className="text-sm text-text">{citation.label}</span>
                        </div>
                        <div className="mt-2 break-all text-xs text-muted">{citation.pageUrl}</div>
                        <div className="mt-1 text-sm text-text">{citation.excerpt}</div>
                      </div>
                    ))
                  ) : (
                    <div className="text-sm text-muted">No citations captured yet. Start a crawl to populate page-level evidence.</div>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Page inventory</CardTitle>
              <CardDescription>Discovered pages, confidence scores, and page-level evidence live here so source tracing stays explicit.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {pageInventory.length ? (
                pageInventory.map((page: PageInventoryItem) => (
                  <div key={page.url} className="rounded-2xl border border-line bg-panel-2 p-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <div className="font-medium text-text">{page.title || page.url}</div>
                        <div className="mt-1 flex flex-wrap gap-2">
                          <Badge>{pageSourceLabel(page.source)}</Badge>
                          <Badge className={page.status === "failed" ? "border-rose-500/40 bg-rose-500/10 text-rose-100" : page.status === "blocked" ? "border-amber-500/40 bg-amber-500/10 text-amber-100" : "border-emerald-500/40 bg-emerald-500/10 text-emerald-100"}>
                            {pageStatusLabel(page.status)}
                          </Badge>
                          <Badge className={confidenceBadgeClass(page.confidence)}>{page.confidence}%</Badge>
                        </div>
                      </div>
                      <div className="text-right text-xs text-muted">
                        <div>Depth {page.depth}</div>
                        <div>{page.ctaCount} CTA{page.ctaCount === 1 ? "" : "s"}</div>
                      </div>
                    </div>
                    <div className="mt-2 break-all text-xs text-muted">{page.url}</div>
                    <div className="mt-3 text-sm text-text">{page.summary || "No summary captured for this page."}</div>
                    {page.citations.length ? (
                      <div className="mt-3 space-y-2">
                        {page.citations.map((citation, index) => (
                          <div key={`${page.url}-${index}`} className="rounded-xl border border-line bg-panel px-3 py-2">
                            <div className="flex flex-wrap items-center gap-2">
                              <Badge>{citation.evidenceType}</Badge>
                              <Badge className={confidenceBadgeClass(citation.confidence)}>{citation.confidence}%</Badge>
                              <span className="text-sm text-text">{citation.label}</span>
                            </div>
                            <div className="mt-1 text-xs text-muted">{citation.excerpt}</div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="mt-3 text-xs text-muted">No page citations captured for this page.</div>
                    )}
                    {page.errors.length ? (
                      <div className="mt-3 flex flex-wrap gap-2">
                        {page.errors.map((error) => (
                          <Badge key={error} className="border-rose-500/40 bg-rose-500/10 text-rose-100">
                            {error}
                          </Badge>
                        ))}
                      </div>
                    ) : null}
                  </div>
                ))
              ) : (
                <div className="text-sm text-muted">No discovered pages yet. Start a crawl to populate the inventory.</div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Job history</CardTitle>
              <CardDescription>Import jobs and any later lead-level work will surface here, with timestamps and progress preserved for operator review.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {lead.jobs.length ? (
                lead.jobs.map((job) => (
                  <div key={job.id} className="rounded-2xl border border-line bg-panel-2 p-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <div className="font-medium text-text">{job.step}</div>
                        <div className="text-xs text-muted">{job.jobType}</div>
                      </div>
                      <Badge className={jobBadgeClass(job.status)}>{jobLabel(job.status)}</Badge>
                    </div>
                    <div className="mt-4">
                      <ProgressBar progress={job.progress} label={`Job ${job.id.slice(0, 8)}`} />
                    </div>
                    <div className="mt-3 grid gap-2 text-xs text-muted sm:grid-cols-2">
                      <div>Started: {job.startedAt ? formatDateTime(job.startedAt) : "Not recorded"}</div>
                      <div>Finished: {job.finishedAt ? formatDateTime(job.finishedAt) : "Not recorded"}</div>
                    </div>
                    <div className="mt-3 text-xs text-muted">{job.errorMessage ? `Error: ${job.errorMessage}` : "No job error recorded."}</div>
                  </div>
                ))
              ) : (
                <div className="text-sm text-muted">No jobs have been attached to this lead yet.</div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Linked actions</CardTitle>
              <CardDescription>Jump back to the intake queue or archive the record if needed.</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-3">
              <Link href="/nsa/leads"><Button>Back to leads</Button></Link>
              <Button variant="secondary">
                <Link href={`/nsa/leads/${lead.id}`}>Refresh detail view</Link>
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </PageFrame>
  );
}
