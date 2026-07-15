import Link from "next/link";

import { EmptyState } from "@/components/state/empty-state";
import { PageFrame } from "@/components/shell/page-frame";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { SiteWorkspaceControls } from "@/components/site-workspace-controls";
import { DisableOverrideButton } from "@/components/disable-override-button";
import { getLead, getLeadBrief, getLeadExtraction } from "@/lib/api/leads";
import { getSite } from "@/lib/api/sites";

function formatDateTime(value: string | null | undefined) {
  return value ? new Date(value).toLocaleString() : "Not recorded";
}

export default async function SiteEditPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const [lead, brief, extraction, site] = await Promise.all([getLead(id), getLeadBrief(id), getLeadExtraction(id), getSite(id)]);

  if (!lead) {
    return (
      <PageFrame
        eyebrow="Edit workspace"
        title={`Structured overrides: ${id}`}
        description="No lead record exists for this workspace yet."
      >
        <EmptyState
          title="Workspace source not found"
          description="Create or import the lead first, then generate a preview before editing overrides."
          action={
            <Button>
              <Link href="/nsa/leads">Back to leads</Link>
            </Button>
          }
        />
      </PageFrame>
    );
  }

  return (
    <PageFrame
      eyebrow="Edit workspace"
      title={lead.companyName || "Missing company name"}
      description="Structured overrides are stored separately from generated HTML so approved changes survive regeneration."
    >
      <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <Card>
          <CardHeader>
            <CardTitle>Override controls</CardTitle>
            <CardDescription>Save copy, layout, brand, CTA, motion, and styling edits as durable override records.</CardDescription>
          </CardHeader>
          <CardContent>
            <SiteWorkspaceControls
              siteId={id}
              site={site}
              hasApprovedBrief={brief?.approvalState === "approved"}
              hasExtraction={Boolean(extraction && extraction.version > 0)}
            />
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Active overrides</CardTitle>
              <CardDescription>These records are replayed when the preview is regenerated.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {site?.overrides.length ? (
                site.overrides.map((override) => (
                  <div key={override.id} className="rounded-2xl border border-line bg-panel-2 p-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge>{override.scope}</Badge>
                      <Badge>{override.path}</Badge>
                      <Badge>{override.status}</Badge>
                    </div>
                    <div className="mt-2 text-sm text-text">{override.value}</div>
                    <div className="mt-2 text-xs text-muted">{override.reason || "No reason captured."}</div>
                    <div className="mt-2 grid gap-1 text-xs text-muted">
                      <div>Previous: {override.previousValue || "Not recorded"}</div>
                      <div>Source: {override.sourceType}</div>
                      <div>Version: {override.version}</div>
                      <div>Created: {formatDateTime(override.createdAt)}</div>
                    </div>
                    {override.status === "active" ? (
                      <div className="mt-3">
                        <DisableOverrideButton siteId={id} overrideId={override.id} />
                      </div>
                    ) : null}
                  </div>
                ))
              ) : (
                <div className="text-sm text-muted">No override records yet. Use the form to store the first approved change.</div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Current site state</CardTitle>
              <CardDescription>This is the current generation version that overrides will be applied against.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm text-text">
              <div>Preview slug: {site?.previewSlug || "Not generated yet"}</div>
              <div>Version: {site?.version ?? 0}</div>
              <div>Theme: {site?.themeName || "Not selected"}</div>
              <div>Readiness: {site?.readinessStatus || "blocked"}</div>
            </CardContent>
          </Card>
        </div>
      </div>
    </PageFrame>
  );
}
