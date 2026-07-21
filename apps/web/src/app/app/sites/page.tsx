"use client";

import Image from "next/image";
import Link from "next/link";
import { ExternalLink, MoreHorizontal, RefreshCw, Search, Trash2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { EmptyState } from "@/components/state/empty-state";
import { ErrorState } from "@/components/state/error-state";
import { LoadingState } from "@/components/state/loading-state";
import { PageFrame } from "@/components/shell/page-frame";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { deleteSite, getSites } from "@/lib/api/sites";
import type { GeneratedSite, SiteReadinessStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

type ReadinessFilter = SiteReadinessStatus | "all";

function qualityScoreDisplay(site: GeneratedSite): { text: string; colorClass: string } {
  if (site.readinessStatus === "blocked") {
    return { text: "Blocked", colorClass: "text-rose-400" };
  }
  const hasScreenshotQA = site.screenshotRefs && site.screenshotRefs.length > 0;
  if (!hasScreenshotQA) {
    const score = site.qualityScore ?? 0;
    if (score === 0) return { text: "— / 100", colorClass: "text-muted" };
    return { text: `~${score} / 100`, colorClass: "text-amber-400" };
  }
  const score = site.qualityScore ?? 0;
  if (score >= 90) return { text: `${score} / 100`, colorClass: "text-emerald-400" };
  if (score >= 75) return { text: `${score} / 100`, colorClass: "text-yellow-400" };
  if (score >= 55) return { text: `${score} / 100`, colorClass: "text-orange-400" };
  return { text: `${score} / 100`, colorClass: "text-rose-400" };
}

function readinessBadgeClass(status: SiteReadinessStatus): string {
  if (status === "published") return "border-emerald-400/60 bg-emerald-400/15 text-emerald-100 font-semibold";
  if (status === "ready_to_publish") return "border-emerald-500/40 bg-emerald-500/10 text-emerald-100";
  if (status === "ready_for_review") return "border-sky-500/40 bg-sky-500/10 text-sky-100";
  if (status === "needs_review") return "border-amber-500/40 bg-amber-500/10 text-amber-100";
  return "border-rose-500/40 bg-rose-500/10 text-rose-100";
}

const READINESS_LABELS: Record<SiteReadinessStatus, string> = {
  blocked: "Blocked",
  needs_review: "Needs review",
  ready_for_review: "Ready for QA",
  ready_to_publish: "Ready to publish",
  published: "Published",
};

type FilterChipProps = {
  label: string;
  count: number;
  active: boolean;
  color: string;
  onClick: () => void;
};

function FilterChip({ label, count, active, color, onClick }: FilterChipProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-2xl border px-4 py-2 text-sm transition",
        active
          ? `border-${color}-500/60 bg-${color}-500/15 text-${color}-200`
          : "border-line bg-panel-2 text-muted hover:border-white/20 hover:text-text"
      )}
    >
      <span className="font-semibold">{count}</span>
      <span className="ml-1.5">{label}</span>
    </button>
  );
}

type Counts = Record<ReadinessFilter, number>;

export default function SitesPage() {
  const [sites, setSites] = useState<GeneratedSite[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<ReadinessFilter>("all");
  const [searchInput, setSearchInput] = useState("");
  const [q, setQ] = useState("");
  const [refreshSeed, setRefreshSeed] = useState(0);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getSites({ limit: 200 });
      setSites(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load websites.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load, refreshSeed]);

  async function handleDelete(siteId: string) {
    setDeletingId(siteId);
    try {
      await deleteSite(siteId);
      setSites((prev) => prev.filter((s) => s.id !== siteId));
    } catch {
      // silently restore — the card stays, user can retry
    } finally {
      setDeletingId(null);
    }
  }

  const counts: Counts = {
    all: sites.length,
    blocked: sites.filter((s) => s.readinessStatus === "blocked").length,
    needs_review: sites.filter((s) => s.readinessStatus === "needs_review").length,
    ready_for_review: sites.filter((s) => s.readinessStatus === "ready_for_review").length,
    ready_to_publish: sites.filter((s) => s.readinessStatus === "ready_to_publish").length,
    published: sites.filter((s) => s.readinessStatus === "published").length,
  };

  const filtered = sites.filter((s) => {
    if (filter !== "all" && s.readinessStatus !== filter) return false;
    if (q) {
      const name = (s.sourceAttribution?.companyName ?? "").toLowerCase();
      const domain = (s.sourceAttribution?.normalizedDomain ?? "").toLowerCase();
      const search = q.toLowerCase();
      if (!name.includes(search) && !domain.includes(search)) return false;
    }
    return true;
  });

  const filterChips: Array<{ key: ReadinessFilter; label: string; color: string }> = [
    { key: "all", label: "All", color: "white" },
    { key: "blocked", label: "Blocked", color: "rose" },
    { key: "needs_review", label: "Needs review", color: "amber" },
    { key: "ready_for_review", label: "Ready for QA", color: "sky" },
    { key: "ready_to_publish", label: "Ready to publish", color: "emerald" },
    { key: "published", label: "Published", color: "emerald" },
  ];

  function applyFilter(next: ReadinessFilter) {
    setFilter(filter === next && next !== "all" ? "all" : next);
  }

  function applySearch() {
    setQ(searchInput.trim());
  }

  return (
    <PageFrame
      eyebrow="Websites"
      title="Websites"
      description="Library of all generated sites. Browse, filter, preview, and manage site readiness."
    >
      {/* Summary strip */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/5 px-4 py-3">
          <div className="text-xs uppercase tracking-[0.18em] text-muted">Ready to publish</div>
          <div className="mt-1 text-2xl font-semibold text-emerald-300">
            {counts.ready_to_publish + counts.published}
          </div>
        </div>
        <div className="rounded-2xl border border-amber-500/20 bg-amber-500/5 px-4 py-3">
          <div className="text-xs uppercase tracking-[0.18em] text-muted">Needs QA</div>
          <div className="mt-1 text-2xl font-semibold text-amber-300">
            {counts.needs_review + counts.ready_for_review}
          </div>
        </div>
        <div className="rounded-2xl border border-rose-500/20 bg-rose-500/5 px-4 py-3">
          <div className="text-xs uppercase tracking-[0.18em] text-muted">Blocked</div>
          <div className="mt-1 text-2xl font-semibold text-rose-300">{counts.blocked}</div>
        </div>
        <div className="rounded-2xl border border-line bg-panel-2 px-4 py-3">
          <div className="text-xs uppercase tracking-[0.18em] text-muted">Published</div>
          <div className="mt-1 text-2xl font-semibold text-text">{counts.published}</div>
        </div>
      </div>

      {/* Filters + search */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap gap-2">
          {filterChips.map((chip) => (
            <FilterChip
              key={chip.key}
              label={chip.label}
              count={counts[chip.key]}
              active={filter === chip.key}
              color={chip.color}
              onClick={() => applyFilter(chip.key)}
            />
          ))}
        </div>
        <div className="flex gap-2">
          <Input
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search company or domain"
            className="w-56"
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                applySearch();
              }
            }}
          />
          <Button variant="secondary" onClick={applySearch}>
            <Search className="h-4 w-4" />
          </Button>
          <Button variant="ghost" onClick={() => setRefreshSeed((s) => s + 1)}>
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {error ? <ErrorState title="Failed to load websites" description={error} /> : null}

      {loading ? (
        <LoadingState label="Loading websites…" />
      ) : filtered.length === 0 ? (
        <EmptyState
          title={
            filter !== "all"
              ? `No sites in "${READINESS_LABELS[filter as SiteReadinessStatus]}"`
              : q
              ? `No results for "${q}"`
              : "No generated websites yet"
          }
          description="Generate a preview from an approved lead brief and it will appear here."
          action={
            <Button>
              <Link href="/app/leads">Go to leads</Link>
            </Button>
          }
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {filtered.map((site) => {
            const companyName =
              site.sourceAttribution?.companyName ||
              site.sourceAttribution?.normalizedDomain ||
              site.id.slice(0, 8);
            const domain = site.sourceAttribution?.normalizedDomain ?? "";
            const previewPath = site.previewUrl || `/st/${site.previewSlug}`;
            const score = qualityScoreDisplay(site);
            const hasScreenshotQA = site.screenshotRefs && site.screenshotRefs.length > 0;

            const screenshotUrl = site.screenshotRefs?.[0]?.url ?? null;
            const variantSuffix = site.variantLabel || site.variantType || null;
            const displayTitle = companyName + (variantSuffix ? ` · ${variantSuffix}` : "");

            const isDeleting = deletingId === site.id;

            return (
              <Card key={site.id} className={cn("flex flex-col overflow-hidden transition-opacity", isDeleting && "opacity-50 pointer-events-none")}>
                <div className="relative h-28 w-full border-b border-line">
                  {screenshotUrl ? (
                    <Image
                      src={screenshotUrl}
                      alt={`Preview of ${companyName}`}
                      fill
                      className="object-cover object-top"
                      unoptimized
                    />
                  ) : (
                    <Link href={previewPath} target="_blank" className="block h-full">
                      <div className="flex h-full w-full items-center justify-center bg-panel-2 transition hover:bg-panel-1">
                        <ExternalLink className="h-4 w-4 text-muted" />
                      </div>
                    </Link>
                  )}
                  {/* 3-dot menu */}
                  <div className="absolute right-2 top-2">
                    <Popover>
                      <PopoverTrigger
                        className="flex h-7 w-7 items-center justify-center rounded-lg bg-black/50 text-white/80 backdrop-blur-sm transition hover:bg-black/70"
                        aria-label="Site options"
                      >
                        <MoreHorizontal className="h-4 w-4" />
                      </PopoverTrigger>
                      <PopoverContent className="w-40 p-1" side="bottom" align="end">
                        <button
                          type="button"
                          onClick={() => void handleDelete(site.id)}
                          className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-rose-300 transition hover:bg-rose-500/10"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                          Delete
                        </button>
                      </PopoverContent>
                    </Popover>
                  </div>
                </div>
                <CardContent className="flex flex-1 flex-col gap-3 p-4">
                  <div>
                    <div className="font-semibold text-text">{displayTitle}</div>
                    {domain ? <div className="mt-0.5 text-xs text-muted">{domain}</div> : null}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Badge className={readinessBadgeClass(site.readinessStatus)}>
                      {READINESS_LABELS[site.readinessStatus]}
                    </Badge>
                    {site.themeName ? (
                      <Badge className="border-white/10 bg-white/5 text-text">{site.themeName}</Badge>
                    ) : null}
                    {site.paletteMode ? (
                      <Badge className="border-white/10 bg-white/5 text-text">{site.paletteMode}</Badge>
                    ) : null}
                  </div>
                  <div className="text-sm">
                    <span className="text-xs uppercase tracking-[0.18em] text-muted">Score </span>
                    <span className={score.colorClass}>{score.text}</span>
                    {!hasScreenshotQA && site.readinessStatus !== "blocked" ? (
                      <span className="ml-1 text-xs text-muted">(QA pending)</span>
                    ) : null}
                  </div>
                  <div className="mt-auto flex gap-2 pt-2">
                    <Button variant="secondary" className="flex-1">
                      <Link href={`/app/sites/${site.id}`}>Open spec</Link>
                    </Button>
                    <Button className="flex-1">
                      <Link href={previewPath} target="_blank" className="flex items-center gap-1.5">
                        Preview
                        <ExternalLink className="h-3.5 w-3.5" />
                      </Link>
                    </Button>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </PageFrame>
  );
}
