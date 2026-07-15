import Link from "next/link";
import { ExternalLink } from "lucide-react";

import { EmptyState } from "@/components/state/empty-state";
import { PageFrame } from "@/components/shell/page-frame";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getSites } from "@/lib/api/sites";
import type { GeneratedSite } from "@/lib/types";

function formatDate(value: string): string {
  return new Date(value).toLocaleString();
}

function readinessTone(status: GeneratedSite["readinessStatus"]): string {
  if (status === "ready_to_publish" || status === "published") return "border-emerald-500/40 bg-emerald-500/10 text-emerald-100";
  if (status === "ready_for_review" || status === "needs_review") return "border-amber-500/40 bg-amber-500/10 text-amber-100";
  return "border-rose-500/40 bg-rose-500/10 text-rose-100";
}

export default async function SitesPage() {
  const sites = await getSites({ limit: 50 });

  const readyCount = sites.filter((site) => site.readinessStatus === "ready_to_publish" || site.readinessStatus === "published").length;
  const reviewCount = sites.filter((site) => site.readinessStatus === "ready_for_review" || site.readinessStatus === "needs_review").length;
  const blockedCount = sites.filter((site) => site.readinessStatus === "blocked").length;

  return (
    <PageFrame
      eyebrow="Websites"
      title="Generated website library"
      description="Browse every generated preview, inspect the source-backed site spec, and open the public preview URL."
    >
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardDescription>Ready or published</CardDescription>
            <CardTitle className="text-3xl">{readyCount}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Needs review</CardDescription>
            <CardTitle className="text-3xl">{reviewCount}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Blocked</CardDescription>
            <CardTitle className="text-3xl">{blockedCount}</CardTitle>
          </CardHeader>
        </Card>
      </div>

      {sites.length ? (
        <div className="grid gap-4">
          {sites.map((site) => {
            const companyName = site.sourceAttribution?.companyName || site.sourceAttribution?.normalizedDomain || site.id.slice(0, 8);
            const previewPath = site.previewUrl || `/sites/${site.previewSlug}`;
            return (
              <Card key={site.id}>
                <CardHeader>
                  <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                    <div className="space-y-2">
                      <div className="flex flex-wrap gap-2">
                        <Badge className={readinessTone(site.readinessStatus)}>{site.readinessStatus}</Badge>
                        <Badge className="bg-white/6">QA {site.qaStatus}</Badge>
                        <Badge className="bg-white/6">v{site.version}</Badge>
                        <Badge className="bg-white/6">{site.themeName}</Badge>
                        <Badge className="bg-white/6">{site.paletteMode}</Badge>
                      </div>
                      <CardTitle>{companyName}</CardTitle>
                      <CardDescription className="max-w-3xl">
                        {site.heroVariant.headline}
                      </CardDescription>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Button variant="secondary">
                        <Link href={`/nsa/sites/${site.id}`}>Open spec</Link>
                      </Button>
                      <Button>
                        <Link href={previewPath} target="_blank">
                          <ExternalLink className="mr-2 h-4 w-4" />
                          Preview
                        </Link>
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="grid gap-3 text-sm text-muted md:grid-cols-2 xl:grid-cols-4">
                  <div>
                    <div className="text-xs uppercase tracking-[0.2em] text-muted">Preview slug</div>
                    <div className="mt-1 break-all font-mono text-xs text-text">{site.previewSlug}</div>
                  </div>
                  <div>
                    <div className="text-xs uppercase tracking-[0.2em] text-muted">Quality</div>
                    <div className="mt-1 text-text">{site.qualityScore} / 100</div>
                  </div>
                  <div>
                    <div className="text-xs uppercase tracking-[0.2em] text-muted">Source refs</div>
                    <div className="mt-1 text-text">{site.sourceTraceability.length}</div>
                  </div>
                  <div>
                    <div className="text-xs uppercase tracking-[0.2em] text-muted">Updated</div>
                    <div className="mt-1 text-text">{formatDate(site.updatedAt)}</div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      ) : (
        <EmptyState
          title="No generated websites yet"
          description="Generate a preview from an approved lead brief and it will appear in this website library."
          action={
            <Button>
              <Link href="/nsa/leads">Go to leads</Link>
            </Button>
          }
        />
      )}
    </PageFrame>
  );
}
