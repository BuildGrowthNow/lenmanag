"use client";

import { useState } from "react";
import { Filter, ChevronDown, ChevronUp, RefreshCw, AlertTriangle } from "lucide-react";
import { EmptyState } from "@/components/state/empty-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { PageInventoryItem, PageStatus, PageSource } from "@/lib/types";

type FilterState = {
  status: PageStatus | "all";
  hasGaps: boolean | "all";
  confidence: "high" | "medium" | "low" | "all";
  source: PageSource | "all";
};

interface ExtractionReviewClientProps {
  leadId: string;
  pages: PageInventoryItem[];
}

export function ExtractionReviewClient({ leadId, pages }: ExtractionReviewClientProps) {
  const [filterOpen, setFilterOpen] = useState(false);
  const [selectedPage, setSelectedPage] = useState<PageInventoryItem | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [filters, setFilters] = useState<FilterState>({
    status: "all",
    hasGaps: "all",
    confidence: "all",
    source: "all",
  });

  const filteredPages = pages.filter((page) => {
    if (filters.status !== "all" && page.status !== filters.status) return false;
    if (filters.hasGaps !== "all") {
      const hasGaps = page.errors.length > 0 || page.confidence < 50;
      if (filters.hasGaps !== hasGaps) return false;
    }
    if (filters.confidence !== "all") {
      if (filters.confidence === "high" && page.confidence < 75) return false;
      if (filters.confidence === "medium" && (page.confidence < 50 || page.confidence >= 75)) return false;
      if (filters.confidence === "low" && page.confidence >= 50) return false;
    }
    if (filters.source !== "all" && page.source !== filters.source) return false;
    return true;
  });

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      // Refresh will be handled by redirecting to the page
      window.location.href = `/nsa/leads/${leadId}/extraction`;
    } catch (error) {
      console.error("Failed to refresh extraction:", error);
    } finally {
      setIsRefreshing(false);
    }
  };

  const confidenceBadgeClass = (confidence: number) => {
    if (confidence >= 75) return "border-emerald-500/40 bg-emerald-500/10 text-emerald-100";
    if (confidence >= 50) return "border-amber-500/40 bg-amber-500/10 text-amber-100";
    return "border-rose-500/40 bg-rose-500/10 text-rose-100";
  };

  const pageStatusBadgeClass = (status: PageStatus) => {
    if (status === "failed") return "border-rose-500/40 bg-rose-500/10 text-rose-100";
    if (status === "blocked") return "border-amber-500/40 bg-amber-500/10 text-amber-100";
    return "border-emerald-500/40 bg-emerald-500/10 text-emerald-100";
  };

  const pageStatusLabel = (status: PageStatus) => {
    if (status === "crawled") return "Crawled";
    if (status === "failed") return "Failed";
    if (status === "blocked") return "Blocked";
    return "Discovered";
  };

  const pageSourceLabel = (source: PageSource) => {
    if (source === "homepage") return "Homepage";
    if (source === "sitemap") return "Sitemap";
    return "Internal link";
  };

  return (
    <>
      {/* Page Inventory Card */}
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between gap-4">
            <div>
              <CardTitle>Page inventory</CardTitle>
              <CardDescription>
                {filteredPages.length} of {pages.length} pages shown. Click a page to view details.
              </CardDescription>
            </div>
            <Button
              variant="secondary"
              onClick={() => setFilterOpen(!filterOpen)}
            >
              <Filter className="h-4 w-4 mr-2" />
              Filters
              {filterOpen ? <ChevronUp className="h-4 w-4 ml-2" /> : <ChevronDown className="h-4 w-4 ml-2" />}
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Filters */}
          {filterOpen && (
            <div className="rounded-2xl border border-line bg-panel-2 p-4 space-y-4">
              <div className="grid gap-4 md:grid-cols-4">
                <div>
                  <label className="text-xs uppercase tracking-[0.18em] text-muted">Status</label>
                  <select
                    className="mt-2 w-full rounded-lg border border-line bg-panel px-3 py-2 text-sm text-text"
                    value={filters.status}
                    onChange={(e) => setFilters({ ...filters, status: e.target.value as FilterState["status"] })}
                  >
                    <option value="all">All statuses</option>
                    <option value="crawled">Crawled</option>
                    <option value="failed">Failed</option>
                    <option value="blocked">Blocked</option>
                    <option value="discovered">Discovered</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs uppercase tracking-[0.18em] text-muted">Has gaps</label>
                  <select
                    className="mt-2 w-full rounded-lg border border-line bg-panel px-3 py-2 text-sm text-text"
                    value={String(filters.hasGaps)}
                    onChange={(e) => setFilters({ ...filters, hasGaps: e.target.value === "all" ? "all" : e.target.value === "true" })}
                  >
                    <option value="all">All</option>
                    <option value="true">Has gaps</option>
                    <option value="false">No gaps</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs uppercase tracking-[0.18em] text-muted">Confidence</label>
                  <select
                    className="mt-2 w-full rounded-lg border border-line bg-panel px-3 py-2 text-sm text-text"
                    value={filters.confidence}
                    onChange={(e) => setFilters({ ...filters, confidence: e.target.value as FilterState["confidence"] })}
                  >
                    <option value="all">All levels</option>
                    <option value="high">High (75%+)</option>
                    <option value="medium">Medium (50-74%)</option>
                    <option value="low">Low (&lt;50%)</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs uppercase tracking-[0.18em] text-muted">Source</label>
                  <select
                    className="mt-2 w-full rounded-lg border border-line bg-panel px-3 py-2 text-sm text-text"
                    value={filters.source}
                    onChange={(e) => setFilters({ ...filters, source: e.target.value as FilterState["source"] })}
                  >
                    <option value="all">All sources</option>
                    <option value="homepage">Homepage</option>
                    <option value="sitemap">Sitemap</option>
                    <option value="internal_link">Internal link</option>
                  </select>
                </div>
              </div>
            </div>
          )}

          {/* Page Table */}
          {filteredPages.length > 0 ? (
            <div className="space-y-2">
              {filteredPages.map((page) => (
                <div
                  key={page.url}
                  className="rounded-2xl border border-line bg-panel-2 p-4 cursor-pointer hover:border-accent/50 transition-colors"
                  onClick={() => setSelectedPage(page)}
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-text truncate">{page.title || page.url}</div>
                      <div className="mt-1 flex flex-wrap gap-2">
                        <Badge>{pageSourceLabel(page.source)}</Badge>
                        <Badge className={pageStatusBadgeClass(page.status)}>
                          {pageStatusLabel(page.status)}
                        </Badge>
                        <Badge className={confidenceBadgeClass(page.confidence)}>
                          {page.confidence}%
                        </Badge>
                      </div>
                    </div>
                    <div className="flex items-center gap-3 text-right text-xs text-muted">
                      <div>Depth {page.depth}</div>
                      <div>{page.ctaCount} CTA{page.ctaCount === 1 ? "" : "s"}</div>
                      {page.errors.length > 0 && (
                        <Badge className="border-rose-500/40 bg-rose-500/10 text-rose-100">
                          {page.errors.length} gap{page.errors.length === 1 ? "" : "s"}
                        </Badge>
                      )}
                    </div>
                  </div>
                  <div className="mt-2 break-all text-xs text-muted truncate">{page.url}</div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              title="No pages match filters"
              description="Adjust the filter criteria to see more pages."
            />
          )}
        </CardContent>
      </Card>

      {/* Page Detail Drawer */}
      {selectedPage && (
        <Card className="border-accent/50">
          <CardHeader>
            <div className="flex items-start justify-between gap-4">
              <div>
                <CardTitle>Page details</CardTitle>
                <CardDescription>Detailed view of crawled page data, citations, and gaps.</CardDescription>
              </div>
              <Button variant="ghost" onClick={() => setSelectedPage(null)}>
                Close
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 md:grid-cols-2">
              <div className="rounded-2xl border border-line bg-panel-2 p-4">
                <div className="text-xs uppercase tracking-[0.18em] text-muted">Page URL</div>
                <div className="mt-2 break-all text-sm text-text">{selectedPage.url}</div>
              </div>
              <div className="rounded-2xl border border-line bg-panel-2 p-4">
                <div className="text-xs uppercase tracking-[0.18em] text-muted">Status & confidence</div>
                <div className="mt-2 flex flex-wrap gap-2">
                  <Badge className={pageStatusBadgeClass(selectedPage.status)}>
                    {pageStatusLabel(selectedPage.status)}
                  </Badge>
                  <Badge className={confidenceBadgeClass(selectedPage.confidence)}>
                    {selectedPage.confidence}% confidence
                  </Badge>
                  <Badge>{pageSourceLabel(selectedPage.source)}</Badge>
                </div>
              </div>
            </div>

            <div className="rounded-2xl border border-line bg-panel-2 p-4">
              <div className="text-xs uppercase tracking-[0.18em] text-muted">Page summary</div>
              <div className="mt-2 text-sm text-text">
                {selectedPage.summary || "No summary captured for this page."}
              </div>
              <div className="mt-3 grid gap-2 text-xs text-muted md:grid-cols-2">
                <div>Depth: {selectedPage.depth}</div>
                <div>CTAs found: {selectedPage.ctaCount}</div>
              </div>
            </div>

            {selectedPage.citations.length > 0 && (
              <div className="rounded-2xl border border-line bg-panel-2 p-4">
                <div className="text-xs uppercase tracking-[0.18em] text-muted">Citations</div>
                <div className="mt-3 space-y-2">
                  {selectedPage.citations.map((citation: any, index: number) => (
                    <div key={`${selectedPage.url}-${index}`} className="rounded-xl border border-line bg-panel px-3 py-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge>{citation.evidenceType}</Badge>
                        <Badge className={confidenceBadgeClass(citation.confidence)}>
                          {citation.confidence}%
                        </Badge>
                        <span className="text-sm text-text">{citation.label}</span>
                      </div>
                      <div className="mt-1 text-sm text-text">{citation.excerpt}</div>
                      <div className="mt-1 text-xs text-muted">Source: {citation.pageUrl}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {selectedPage.errors.length > 0 && (
              <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4">
                <div className="text-xs uppercase tracking-[0.18em] text-rose-100">Gaps & errors</div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {selectedPage.errors.map((error: string) => (
                    <Badge key={error} className="border-rose-500/40 bg-rose-500/10 text-rose-100">
                      {error}
                    </Badge>
                  ))}
                </div>
                <div className="mt-3 text-sm text-rose-100/80">
                  These gaps may prevent brief approval. Consider refreshing the extraction or marking this page as non-blocking.
                </div>
              </div>
            )}

            <div className="flex flex-wrap gap-3">
              <Button variant="secondary" onClick={handleRefresh} disabled={isRefreshing}>
                <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? "animate-spin" : ""}`} />
                Refresh extraction
              </Button>
              {selectedPage.errors.length > 0 && (
                <Button variant="secondary" className="border-amber-500/40 bg-amber-500/10 text-amber-100">
                  <AlertTriangle className="h-4 w-4 mr-2" />
                  Flag as blocking
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </>
  );
}
