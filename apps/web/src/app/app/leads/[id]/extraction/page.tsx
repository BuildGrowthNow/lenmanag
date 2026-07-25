"use client";

import Link from "next/link";
import { AlertTriangle } from "lucide-react";
import { useEffect, useState } from "react";

import { PageFrame } from "@/components/shell/page-frame";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ExtractionReviewClient } from "@/components/extraction-review-client";
import { getLead, getLeadExtraction, getLeadPages } from "@/lib/api/leads";
import type { ExtractionStatus, LeadDetail, ExtractionSnapshot, PageInventoryResponse } from "@/lib/types";

function extractionStatusLabel(status: ExtractionStatus) {
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

function confidenceBadgeClass(confidence: number) {
  if (confidence >= 75) return "border-emerald-500/40 bg-emerald-500/10 text-emerald-100";
  if (confidence >= 50) return "border-amber-500/40 bg-amber-500/10 text-amber-100";
  return "border-rose-500/40 bg-rose-500/10 text-rose-100";
}

function extractionBadgeClass(status: ExtractionStatus) {
  if (status === "running") return "border-blue-500/40 bg-blue-500/10 text-blue-100";
  if (status === "queued") return "border-sky-500/40 bg-sky-500/10 text-sky-100";
  if (status === "partial") return "border-amber-500/40 bg-amber-500/10 text-amber-100";
  if (status === "failed") return "border-rose-500/40 bg-rose-500/10 text-rose-100";
  return "border-emerald-500/40 bg-emerald-500/10 text-emerald-100";
}

export default function ExtractionReviewPage({ params }: { params: Promise<{ id: string }> }) {
  const [leadId, setLeadId] = useState<string | null>(null);
  const [lead, setLead] = useState<LeadDetail | null>(null);
  const [extraction, setExtraction] = useState<ExtractionSnapshot | null>(null);
  const [pagesResponse, setPagesResponse] = useState<PageInventoryResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    async function loadParams() {
      const p = await params;
      if (mounted) setLeadId(p.id);
    }
    void loadParams();
    return () => { mounted = false; };
  }, [params]);

  useEffect(() => {
    if (!leadId) return;
    let mounted = true;

    async function loadData() {
      try {
        const [leadData, extractionData, pagesData] = await Promise.all([
          getLead(leadId),
          getLeadExtraction(leadId),
          getLeadPages(leadId),
        ]);

        if (!mounted) return;

        setLead(leadData);
        setExtraction(extractionData);
        setPagesResponse(pagesData);
        setLoading(false);
      } catch (error) {
        console.error("Failed to load extraction data:", error);
        setLoading(false);
      }
    }

    void loadData();
    return () => { mounted = false; };
  }, [leadId]);

  if (loading) {
    return (
      <PageFrame
        eyebrow="Extraction review"
        title="Loading..."
        description="Fetching extraction data..."
      >
        <div className="text-sm text-muted">Loading extraction details...</div>
      </PageFrame>
    );
  }

  if (!lead) {
    return (
      <PageFrame
        eyebrow="Extraction review"
        title="Lead not found"
        description="The lead record does not exist."
      >
        <Link href="/app/leads">
          <Button>Back to leads</Button>
        </Link>
      </PageFrame>
    );
  }

  const extractionData = extraction || {
    id: "pending",
    leadId: leadId,
    crawlStatus: "idle" as ExtractionStatus,
    sitemapStatus: "unknown",
    pagesDiscovered: 0,
    pagesCrawled: 0,
    canonicalWebsiteUrl: lead.websiteUrl,
    detectedWebsiteUrl: lead.detectedWebsiteUrl,
    confidenceScore: 0,
    gapItems: ["crawl_not_started"],
    errors: [],
    updatedAt: lead.updatedAt,
  };

  const pages = pagesResponse?.pages || [];
  const gapItems = pagesResponse?.gapItems || extractionData.gapItems;

  const hasCriticalGaps = gapItems.some((gap) => 
    ["homepage_unreachable", "low_confidence_extraction", "page_summaries_sparse"].includes(gap)
  );

  return (
    <PageFrame
      eyebrow="Extraction review"
      title={`${lead.companyName || "Unknown"} - Page Inventory`}
      description="Inspect raw crawled pages, per-page summaries, citations, and gap lists before approving the brief."
    >
      <div className="space-y-4">
        {/* Extraction Summary Card */}
        <Card>
          <CardHeader>
            <div className="flex items-start justify-between gap-4">
              <div>
                <CardTitle>Extraction summary</CardTitle>
                <CardDescription>Crawl status, confidence score, and overall extraction health.</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 md:grid-cols-2">
              <div className="rounded-2xl border border-line bg-panel-2 p-4">
                <div className="text-xs uppercase tracking-[0.18em] text-muted">Crawl status</div>
                <div className="mt-2 flex flex-wrap gap-2">
                  <Badge className={extractionBadgeClass(extractionData.crawlStatus)}>
                    {extractionStatusLabel(extractionData.crawlStatus)}
                  </Badge>
                  <Badge>{sitemapStatusLabel(extractionData.sitemapStatus)} sitemap</Badge>
                  <Badge className={confidenceBadgeClass(extractionData.confidenceScore)}>
                    {extractionData.confidenceScore}% confidence
                  </Badge>
                </div>
                <div className="mt-3 grid gap-2 text-xs text-muted">
                  <div>Canonical: {extractionData.canonicalWebsiteUrl}</div>
                  <div>Detected: {extractionData.detectedWebsiteUrl || "No redirect"}</div>
                  <div>Pages discovered: {extractionData.pagesDiscovered}</div>
                  <div>Pages crawled: {extractionData.pagesCrawled}</div>
                </div>
              </div>
              <div className="rounded-2xl border border-line bg-panel-2 p-4">
                <div className="text-xs uppercase tracking-[0.18em] text-muted">Gaps & errors</div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {gapItems.length ? (
                    gapItems.map((gap) => (
                      <Badge key={gap} className="border-amber-500/40 bg-amber-500/10 text-amber-100">
                        {gap}
                      </Badge>
                    ))
                  ) : (
                    <span className="text-sm text-muted">No gaps recorded</span>
                  )}
                </div>
                {hasCriticalGaps && (
                  <div className="mt-3 rounded-xl border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-rose-100">
                    <div className="flex items-start gap-2">
                      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                      <div className="text-sm">
                        <div className="font-medium">Critical gaps detected</div>
                        <div className="mt-1 text-xs text-rose-100/80">
                          Brief approval is blocked until critical gaps are resolved.
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Page Inventory Client Component */}
        <ExtractionReviewClient 
          leadId={leadId} 
          pages={pages} 
        />

        {/* Linked Actions */}
        <Card>
          <CardHeader>
            <CardTitle>Linked actions</CardTitle>
            <CardDescription>Jump back to the lead workspace or other related surfaces.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-3">
            <Button>
              <Link href={`/app/leads/${leadId}`}>Back to lead workspace</Link>
            </Button>
            <Button variant="secondary">
              <Link href={`/app/leads/${leadId}/extraction`}>Refresh extraction review</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </PageFrame>
  );
}
