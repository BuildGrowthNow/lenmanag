import Link from "next/link";

import { EmptyState } from "@/components/state/empty-state";
import { PageFrame } from "@/components/shell/page-frame";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getLead, getLeadBrief, getLeadExtraction } from "@/lib/api/leads";

export default async function SiteBriefPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const [lead, brief, extraction] = await Promise.all([getLead(id), getLeadBrief(id), getLeadExtraction(id)]);

  if (!lead) {
    return (
      <PageFrame eyebrow="Brief" title={`Site brief: ${id}`} description="No lead record exists for this workspace yet.">
        <EmptyState
          title="Lead source not found"
          description="Create or import a lead first, then generate extraction data and a site brief from the workspace."
          action={
            <Button asChild>
              <Link href="/nsa/leads">Back to leads</Link>
            </Button>
          }
        />
      </PageFrame>
    );
  }

  const hasExtraction = Boolean(extraction && extraction.version > 0);

  return (
    <PageFrame
      eyebrow="Brief"
      title={lead.companyName || `Site brief: ${id}`}
      description="The brief stays grounded in public crawl evidence, exposed as traceable recommendations, and ready for operator review before generation."
    >
      {brief ? (
        <div className="grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
          <Card>
            <CardHeader>
              <CardTitle>Brief overview</CardTitle>
              <CardDescription>Source-backed and inferred recommendations stay versioned so operators can compare every edit.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 text-sm text-text">
              <div className="grid gap-3 md:grid-cols-2">
                <div className="rounded-2xl border border-line bg-panel-2 p-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-muted">Version</div>
                  <div className="mt-2 text-text">v{brief.version}</div>
                  <div className="mt-1 text-xs text-muted">Approval: {brief.approvalState}</div>
                </div>
                <div className="rounded-2xl border border-line bg-panel-2 p-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-muted">Confidence</div>
                  <div className="mt-2 text-text">{brief.confidenceScore}%</div>
                  <div className="mt-1 text-xs text-muted">Needs review: {brief.needsReview ? "Yes" : "No"}</div>
                </div>
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                <div className="rounded-2xl border border-line bg-panel-2 p-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-muted">Company summary</div>
                  <div className="mt-2 text-text">{brief.companySummary.value}</div>
                  <div className="mt-2 text-xs text-muted">{brief.companySummary.evidence.inferenceLabel}</div>
                </div>
                <div className="rounded-2xl border border-line bg-panel-2 p-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-muted">Value proposition</div>
                  <div className="mt-2 text-text">{brief.valuePropositionSummary.value}</div>
                  <div className="mt-2 text-xs text-muted">{brief.valuePropositionSummary.evidence.inferenceLabel}</div>
                </div>
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                <div className="rounded-2xl border border-line bg-panel-2 p-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-muted">Audience hypothesis</div>
                  <div className="mt-2 text-text">{brief.audienceHypothesis.value}</div>
                  <div className="mt-2 text-xs text-muted">{brief.audienceHypothesis.evidence.inferenceLabel}</div>
                </div>
                <div className="rounded-2xl border border-line bg-panel-2 p-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-muted">Conversion angle</div>
                  <div className="mt-2 text-text">{brief.conversionAngle.value}</div>
                  <div className="mt-2 text-xs text-muted">{brief.conversionAngle.evidence.inferenceLabel}</div>
                </div>
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                <div className="rounded-2xl border border-line bg-panel-2 p-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-muted">Hero direction</div>
                  <div className="mt-2 text-text">{brief.recommendedHero.value}</div>
                  <div className="mt-2 text-xs text-muted">{brief.recommendedHero.evidence.inferenceLabel}</div>
                </div>
                <div className="rounded-2xl border border-line bg-panel-2 p-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-muted">Tone profile</div>
                  <div className="mt-2 text-text">{brief.toneProfile.value}</div>
                  <div className="mt-2 text-xs text-muted">{brief.toneProfile.evidence.inferenceLabel}</div>
                </div>
              </div>

              <div className="rounded-2xl border border-line bg-panel-2 p-4">
                <div className="text-xs uppercase tracking-[0.18em] text-muted">Recommended sections</div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {brief.recommendedSections.length ? (
                    brief.recommendedSections.map((section) => <Badge key={section.title}>{section.title}</Badge>)
                  ) : (
                    <span className="text-sm text-muted">No section stack recommendations were recorded.</span>
                  )}
                </div>
              </div>

              <div className="rounded-2xl border border-line bg-panel-2 p-4">
                <div className="text-xs uppercase tracking-[0.18em] text-muted">Review notes</div>
                <div className="mt-2 whitespace-pre-wrap text-text">{brief.reviewNotes || "No review notes recorded."}</div>
              </div>

              <div className="rounded-2xl border border-line bg-panel-2 p-4">
                <div className="text-xs uppercase tracking-[0.18em] text-muted">Missing requirements</div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {brief.missingRequirements.length ? (
                    brief.missingRequirements.map((item) => <Badge key={item} className="border-amber-500/40 bg-amber-500/10 text-amber-100">{item}</Badge>)
                  ) : (
                    <span className="text-sm text-muted">No blockers were recorded on this brief.</span>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          <div className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Traceability</CardTitle>
                <CardDescription>Source citations and brand asset provenance stay visible for operator review.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="rounded-2xl border border-line bg-panel-2 p-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-muted">Source citations</div>
                  <div className="mt-3 space-y-2">
                    {brief.sourceCitations.length ? (
                      brief.sourceCitations.map((citation, index) => (
                        <div key={`${citation.kind}-${citation.sourceUrl}-${index}`} className="rounded-xl border border-line bg-panel px-3 py-2 text-sm">
                          <div className="flex flex-wrap items-center gap-2">
                            <Badge>{citation.kind}</Badge>
                            {citation.evidenceType ? <Badge>{citation.evidenceType}</Badge> : null}
                            {citation.assetType ? <Badge>{citation.assetType}</Badge> : null}
                            <Badge>{citation.confidence}%</Badge>
                            <span className="text-text">{citation.label}</span>
                          </div>
                          <div className="mt-2 break-all text-xs text-muted">{citation.sourceUrl}</div>
                          <div className="mt-1 text-text">{citation.excerpt}</div>
                        </div>
                      ))
                    ) : (
                      <div className="text-sm text-muted">No source citations were captured with this brief.</div>
                    )}
                  </div>
                </div>

                <div className="rounded-2xl border border-line bg-panel-2 p-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-muted">Brand asset provenance</div>
                  <div className="mt-3 space-y-2">
                    {brief.brandAssetProvenance.length ? (
                      brief.brandAssetProvenance.map((reference, index) => (
                        <div key={`${reference.kind}-${reference.sourceUrl}-${index}`} className="rounded-xl border border-line bg-panel px-3 py-2 text-sm">
                          <div className="flex flex-wrap items-center gap-2">
                            <Badge>{reference.kind}</Badge>
                            {reference.assetType ? <Badge>{reference.assetType}</Badge> : null}
                            <Badge>{reference.confidence}%</Badge>
                            <span className="text-text">{reference.label}</span>
                          </div>
                          <div className="mt-2 break-all text-xs text-muted">{reference.sourceUrl}</div>
                          <div className="mt-1 text-text">{reference.excerpt}</div>
                        </div>
                      ))
                    ) : (
                      <div className="text-sm text-muted">No public brand assets were stored for this brief.</div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Extraction status</CardTitle>
                <CardDescription>The brief is only meaningful when it stays anchored to the crawl evidence underneath it.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-sm text-text">
                <div>Extraction status: {extraction?.crawlStatus || "idle"}</div>
                <div>Pages crawled: {extraction?.pagesCrawled ?? 0}</div>
                <div>Has extraction: {hasExtraction ? "Yes" : "No"}</div>
                <div className="flex flex-wrap gap-3 pt-2">
                  <Button asChild>
                    <Link href={`/nsa/leads/${lead.id}`}>Open lead review</Link>
                  </Button>
                  <Button asChild variant="secondary">
                    <Link href={`/nsa/sites/${lead.id}`}>Open site workspace</Link>
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      ) : (
        <EmptyState
          title="Brief data not yet generated"
          description="Run extraction and create the brief from the lead workspace before review can begin."
          action={
            <Button asChild>
              <Link href={`/nsa/leads/${lead.id}`}>Go to lead workspace</Link>
            </Button>
          }
        />
      )}
    </PageFrame>
  );
}
