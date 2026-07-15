import Link from "next/link";

import { PageFrame } from "@/components/shell/page-frame";
import { EmptyState } from "@/components/state/empty-state";
import { LeadBriefReview } from "@/components/lead-brief-review";
import { LeadExtractionControls } from "@/components/lead-extraction-controls";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getLead, getLeadBrief, getLeadExtraction } from "@/lib/api/leads";
import { evaluateExtractionHealth, formatDateTime as formatExtractionDate } from "@/lib/extraction-health";

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

  const extractionHealth = evaluateExtractionHealth(extraction);

  return (
    <PageFrame
      eyebrow="Brief"
      title={lead.companyName || `Site brief: ${id}`}
      description="The brief stays grounded in public crawl evidence, exposed as traceable recommendations, and ready for operator review before generation."
    >
      <div className="space-y-4">
        <LeadBriefReview leadId={lead.id} brief={brief} extractionHealth={extractionHealth} />

        <div className="grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
          <Card>
            <CardHeader>
              <CardTitle>Extraction readiness</CardTitle>
              <CardDescription>Refresh the crawl directly from the site workspace before editing or approving the brief.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 text-sm text-text">
              <div className="rounded-2xl border border-line bg-panel-2 p-4 text-xs text-muted">
                <div className="uppercase tracking-[0.18em]">Latest extraction snapshot</div>
                <div className="mt-2 text-sm text-text">Version {extraction?.version ?? 0}</div>
                <div className="mt-1 text-xs">
                  Updated {formatExtractionDate(extraction?.updatedAt) || "Not recorded"}
                </div>
                <div className="mt-2 flex flex-wrap gap-2">
                  <Badge>{extraction?.crawlStatus ?? "idle"}</Badge>
                  <Badge>{extractionHealth.hasExtraction ? "Has extraction" : "Missing extraction"}</Badge>
                  <Badge>{extraction?.pagesCrawled ?? 0} pages crawled</Badge>
                </div>
              </div>
              <div className="rounded-2xl border border-line bg-panel-2 p-4">
                <LeadExtractionControls leadId={lead.id} extraction={extraction} />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Next actions</CardTitle>
              <CardDescription>Navigate between the lead, brief, and site workspaces without losing context.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 text-sm text-text">
              <div className="rounded-2xl border border-line bg-panel-2 p-4">
                <div className="text-xs uppercase tracking-[0.18em] text-muted">Workspace links</div>
                <div className="mt-3 flex flex-wrap gap-3">
                  <Button asChild>
                    <Link href={`/nsa/leads/${lead.id}`}>Open lead workspace</Link>
                  </Button>
                  <Button asChild variant="secondary">
                    <Link href={`/nsa/sites/${lead.id}`}>Open site workspace</Link>
                  </Button>
                </div>
              </div>
              <div className="rounded-2xl border border-line bg-panel-2 p-4 text-xs text-muted">
                <div className="text-xs uppercase tracking-[0.18em]">Brief status</div>
                {brief ? (
                  <div className="mt-2 space-y-1 text-sm text-text">
                    <div>Version v{brief.version}</div>
                    <div>Approval: {brief.approvalState}</div>
                    <div>Confidence: {brief.confidenceScore}%</div>
                  </div>
                ) : (
                  <div className="mt-2 text-sm text-text">No brief has been generated yet.</div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {!brief ? (
          <EmptyState
            title="Brief data not yet generated"
            description="Run extraction and create the brief from the lead workspace before review can begin."
            action={
              <Button asChild>
                <Link href={`/nsa/leads/${lead.id}`}>Go to lead workspace</Link>
              </Button>
            }
          />
        ) : null}
      </div>
    </PageFrame>
  );
}
