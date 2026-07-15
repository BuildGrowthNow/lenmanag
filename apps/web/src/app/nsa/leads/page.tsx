"use client";

import Link from "next/link";
import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Link2, Merge } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/state/empty-state";
import { ErrorState } from "@/components/state/error-state";
import { LoadingState } from "@/components/state/loading-state";
import { PageFrame } from "@/components/shell/page-frame";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { archiveLead, createLead, importLeads, listLeads } from "@/lib/api/leads";
import { getJob } from "@/lib/api/jobs";
import type { JobResponse, LeadImportResponse, LeadListItem, LeadListResponse, LeadStatus } from "@/lib/types";

const PAGE_SIZE = 25;

const statusFilters: Array<{ label: string; value: LeadStatus | "all" }> = [
  { label: "All", value: "all" },
  { label: "New", value: "new" },
  { label: "Needs review", value: "needs_review" },
  { label: "Archived", value: "archived" }
];

function statusLabel(status: LeadStatus) {
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

function rowStatusClass(status: string) {
  if (status === "created") return "border-emerald-500/40 bg-emerald-500/10 text-emerald-100";
  if (status === "merged") return "border-amber-500/40 bg-amber-500/10 text-amber-100";
  return "border-rose-500/40 bg-rose-500/10 text-rose-100";
}

function rowStatusLabel(status: string) {
  if (status === "created") return "Created";
  if (status === "merged") return "Merged";
  return "Failed";
}

function formatDateTime(value: string | null | undefined) {
  if (!value) return "Not recorded";
  return new Date(value).toLocaleString();
}

function progressWidth(progress: number) {
  return `${Math.max(0, Math.min(100, progress))}%`;
}

function parsePage(value: string | null) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed < 1) return 1;
  return Math.floor(parsed);
}

function LeadProgress({ progress, label }: { progress: number; label: string }) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-3 text-xs text-muted">
        <span>{label}</span>
        <span>{progress}%</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-white/8">
        <div className="h-full rounded-full bg-accent transition-all" style={{ width: progressWidth(progress) }} />
      </div>
    </div>
  );
}

function parseUrlState(value: string | null) {
  return value ? value : "";
}

function LeadUrlStateSync({
  onChange
}: {
  onChange: (nextState: { q: string; status: LeadStatus | "all"; page: number }) => void;
}) {
  const searchParams = useSearchParams();

  useEffect(() => {
    const nextQuery = parseUrlState(searchParams.get("q"));
    const nextStatus = searchParams.get("status");
    const nextPage = parsePage(searchParams.get("page"));

    onChange({
      q: nextQuery,
      status: nextStatus === "new" || nextStatus === "needs_review" || nextStatus === "archived" ? nextStatus : "all",
      page: nextPage
    });
  }, [onChange, searchParams]);

  return null;
}

export default function LeadsPage() {
  const router = useRouter();
  const pathname = usePathname();
  const [query, setQuery] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [statusFilter, setStatusFilter] = useState<LeadStatus | "all">("all");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<LeadListResponse>({ items: [], pagination: { total: 0, limit: PAGE_SIZE, offset: 0 } });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshSeed, setRefreshSeed] = useState(0);
  const [manualSaving, setManualSaving] = useState(false);
  const [importSaving, setImportSaving] = useState(false);
  const [importJobDetails, setImportJobDetails] = useState<JobResponse | null>(null);
  const [showAllImportRows, setShowAllImportRows] = useState(false);
  const [manualForm, setManualForm] = useState({
    companyName: "",
    websiteUrl: "",
    notes: "",
    industry: ""
  });
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [lastImport, setLastImport] = useState<LeadImportResponse | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const handleUrlStateChange = useCallback(
    (nextState: { q: string; status: LeadStatus | "all"; page: number }) => {
      setQuery(nextState.q);
      setSearchInput(nextState.q);
      setStatusFilter(nextState.status);
      setPage(nextState.page);
    },
    []
  );

  const syncUrl = useCallback(
    (nextValues: { q?: string; status?: LeadStatus | "all"; page?: number }) => {
    const params = new URLSearchParams();
    const nextQuery = nextValues.q ?? query;
    const nextStatus = nextValues.status ?? statusFilter;
    const nextPage = nextValues.page ?? page;

    if (nextQuery) {
      params.set("q", nextQuery);
    } else {
      params.delete("q");
    }

    if (nextStatus && nextStatus !== "all") {
      params.set("status", nextStatus);
    } else {
      params.delete("status");
    }

    if (nextPage > 1) {
      params.set("page", String(nextPage));
    } else {
      params.delete("page");
    }

    const suffix = params.toString();
    router.replace(suffix ? `${pathname}?${suffix}` : pathname, { scroll: false });
    },
    [page, pathname, query, router, statusFilter]
  );

  useEffect(() => {
    let active = true;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const offset = (page - 1) * PAGE_SIZE;
        const result = await listLeads({
          q: query || undefined,
          status: statusFilter === "all" ? undefined : statusFilter,
          limit: PAGE_SIZE,
          offset
        });
        if (!active) return;
        setData(result);

        const totalPages = Math.max(1, Math.ceil(result.pagination.total / Math.max(result.pagination.limit, 1)));
    if (page > totalPages && result.pagination.total > 0) {
          setPage(totalPages);
          syncUrl({ page: totalPages });
        }
      } catch (err) {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Failed to load leads.");
      } finally {
        if (active) setLoading(false);
      }
    }
    void load();
    return () => {
      active = false;
    };
  }, [page, query, refreshSeed, statusFilter, syncUrl]);

  const items = data.items;
  const summary = useMemo(() => {
    const activeJobs = items.filter((item) => item.latestJob && (item.latestJob.status === "queued" || item.latestJob.status === "running")).length;
    const needsReview = items.filter((item) => item.status === "needs_review").length;
    return {
      total: data.pagination.total,
      activeJobs,
      needsReview,
      archived: items.filter((item) => item.status === "archived").length
    };
  }, [data.pagination.total, items]);

  async function submitManualLead(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setManualSaving(true);
    setActionMessage(null);
    setError(null);
    try {
      const result = await createLead({
        companyName: manualForm.companyName.trim() || null,
        websiteUrl: manualForm.websiteUrl.trim(),
        industry: manualForm.industry.trim() || null,
        notes: manualForm.notes.trim() || null
      });
      setActionMessage(result.message);
      setManualForm({ companyName: "", websiteUrl: "", notes: "", industry: "" });
      setRefreshSeed((seed) => seed + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create lead.");
    } finally {
      setManualSaving(false);
    }
  }

  async function submitImport(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setImportSaving(true);
    setActionMessage(null);
    setError(null);
    try {
      if (!selectedFile) {
        throw new Error("Choose a CSV file before importing.");
      }
      const result = await importLeads(selectedFile);
      setLastImport(result);
      setShowAllImportRows(false);
      setImportJobDetails(await getJob(result.job.id));
      setActionMessage(`Imported ${result.totalRows} row${result.totalRows === 1 ? "" : "s"} with ${result.createdCount} created and ${result.mergedCount} merged.`);
      setSelectedFile(null);
      setRefreshSeed((seed) => seed + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "CSV import failed.");
    } finally {
      setImportSaving(false);
    }
  }

  function refreshList() {
    setRefreshSeed((seed) => seed + 1);
  }

  function applySearch(nextQuery: string) {
    const trimmed = nextQuery.trim();
    setQuery(trimmed);
    setPage(1);
    syncUrl({ q: trimmed, page: 1 });
  }

  function applyStatus(nextStatus: LeadStatus | "all") {
    setStatusFilter(nextStatus);
    setPage(1);
    syncUrl({ status: nextStatus, page: 1 });
  }

  async function archiveSelectedLead(id: string) {
    setActionMessage(null);
    setError(null);
    try {
      await archiveLead(id);
      setActionMessage("Lead archived.");
      refreshList();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not archive lead.");
    }
  }

  const currentPage = page;
  const totalPages = Math.max(1, Math.ceil(data.pagination.total / Math.max(data.pagination.limit, 1)));
  const startItem = data.pagination.total === 0 ? 0 : data.pagination.offset + 1;
  const endItem = Math.min(data.pagination.offset + items.length, data.pagination.total);
  const mergedRecords = items.filter((item) => item.version > 1).length;

  return (
    <>
      <Suspense fallback={null}>
        <LeadUrlStateSync onChange={handleUrlStateChange} />
      </Suspense>
      <PageFrame
        eyebrow="Leads"
        title="Lead intake workspace"
        description="Import CSV rows or create a single lead manually. Duplicate domains merge into the existing record so provenance stays traceable."
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card>
          <CardHeader>
            <CardDescription>Total leads</CardDescription>
            <CardTitle className="text-3xl">{summary.total}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Needs review</CardDescription>
            <CardTitle className="text-3xl">{summary.needsReview}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Active jobs</CardDescription>
            <CardTitle className="text-3xl">{summary.activeJobs}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Archived</CardDescription>
            <CardTitle className="text-3xl">{summary.archived}</CardTitle>
          </CardHeader>
        </Card>
        </div>

        {error ? <ErrorState title="Lead intake error" description={error} /> : null}
        {actionMessage ? (
          <div className="rounded-3xl border border-line bg-panel px-5 py-4 text-sm text-text">{actionMessage}</div>
        ) : null}

        <div className="grid gap-4 xl:grid-cols-[1fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Manual lead entry</CardTitle>
            <CardDescription>Create one lead without a CSV. Missing company names remain explicit instead of being guessed.</CardDescription>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={submitManualLead}>
              <div className="space-y-2">
                <label className="text-xs uppercase tracking-[0.2em] text-muted">Company name</label>
                <Input
                  value={manualForm.companyName}
                  onChange={(event) => setManualForm((current) => ({ ...current, companyName: event.target.value }))}
                  placeholder="Optional, but helps operators triage"
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs uppercase tracking-[0.2em] text-muted">Website URL</label>
                <Input
                  required
                  value={manualForm.websiteUrl}
                  onChange={(event) => setManualForm((current) => ({ ...current, websiteUrl: event.target.value }))}
                  placeholder="https://example.com"
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs uppercase tracking-[0.2em] text-muted">Industry</label>
                <Input
                  value={manualForm.industry}
                  onChange={(event) => setManualForm((current) => ({ ...current, industry: event.target.value }))}
                  placeholder="Optional"
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs uppercase tracking-[0.2em] text-muted">Notes</label>
                <Textarea
                  value={manualForm.notes}
                  onChange={(event) => setManualForm((current) => ({ ...current, notes: event.target.value }))}
                  placeholder="Any context worth preserving"
                />
              </div>
              <Button type="submit" disabled={manualSaving}>
                {manualSaving ? "Creating..." : "Create lead"}
              </Button>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>CSV import</CardTitle>
            <CardDescription>Upload a CSV with `companyName` and `websiteUrl` columns. Rows with the same domain merge into the existing record.</CardDescription>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={submitImport}>
              <div className="space-y-2">
                <label className="text-xs uppercase tracking-[0.2em] text-muted">CSV file</label>
                <Input
                  type="file"
                  accept=".csv,text/csv"
                  onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
                />
                <p className="text-xs leading-5 text-muted">Column aliases accepted: `company`, `name`, `website`, `url`, `domain`, `notes`, and `industry`.</p>
                <p className="text-xs text-muted">{selectedFile ? `Selected: ${selectedFile.name}` : "No file selected yet."}</p>
              </div>
              <Button type="submit" disabled={importSaving || !selectedFile}>
                {importSaving ? "Importing..." : "Import CSV"}
              </Button>
            </form>

            {lastImport ? (
              <div className="mt-5 rounded-2xl border border-line bg-panel-2 p-4">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="text-sm font-semibold text-text">Latest import job</div>
                    <div className="text-xs text-muted">{lastImport.job.step}</div>
                  </div>
                  <Badge className={jobBadgeClass(lastImport.job.status)}>{jobLabel(lastImport.job.status)}</Badge>
                </div>
                <div className="mt-4">
                  <LeadProgress progress={lastImport.job.progress} label="Batch progress" />
                </div>
                <div className="mt-4 grid gap-2 text-xs text-muted sm:grid-cols-2 xl:grid-cols-4">
                  <div>Created: {lastImport.createdCount}</div>
                  <div>Merged: {lastImport.mergedCount}</div>
                  <div>Failed: {lastImport.failedCount}</div>
                  <div>Job ID: {lastImport.job.id.slice(0, 8)}</div>
                </div>
                {importJobDetails ? (
                  <div className="mt-4 rounded-2xl border border-line bg-panel px-4 py-3 text-xs text-muted">
                    <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
                      <div>Source file: {typeof importJobDetails.metadata.fileName === "string" ? importJobDetails.metadata.fileName : "Unknown"}</div>
                      <div>Rows detected: {typeof importJobDetails.metadata.rowCount === "number" ? importJobDetails.metadata.rowCount : lastImport.totalRows}</div>
                      <div>Linked leads: {importJobDetails.leadIds.length}</div>
                      <div>Started: {formatDateTime(lastImport.job.startedAt)}</div>
                    </div>
                    <div className="mt-2 text-xs text-muted">Finished: {formatDateTime(lastImport.job.finishedAt)}</div>
                  </div>
                ) : null}
                <div className="mt-4 flex items-center justify-between gap-3 text-xs text-muted">
                  <div>
                    Showing {Math.min(showAllImportRows ? lastImport.items.length : 3, lastImport.items.length)} of {lastImport.items.length} row results
                  </div>
                  {lastImport.items.length > 3 ? (
                    <Button type="button" variant="ghost" onClick={() => setShowAllImportRows((current) => !current)}>
                      {showAllImportRows ? "Show fewer" : "Show all"}
                    </Button>
                  ) : null}
                </div>
                <div className="mt-4 space-y-2">
                  {(showAllImportRows ? lastImport.items : lastImport.items.slice(0, 3)).map((item) => (
                    <div key={item.rowNumber} className="rounded-xl border border-line bg-panel px-3 py-2 text-sm">
                      <div className="flex items-center justify-between gap-3">
                        <span>Row {item.rowNumber}</span>
                        <Badge className={rowStatusClass(item.status)}>{rowStatusLabel(item.status)}</Badge>
                      </div>
                      <div className="mt-1 text-xs text-muted">{item.message}</div>
                      {item.status === "merged" ? (
                        <div className="mt-1 text-xs text-amber-100/80">This row merged into an existing lead, so the source trail stays attached to the canonical record.</div>
                      ) : null}
                      {item.status === "failed" ? (
                        <div className="mt-1 text-xs text-rose-100/80">This row stayed unresolved. Fix the missing or invalid fields before retrying the import.</div>
                      ) : null}
                      <div className="mt-3 flex flex-wrap items-center gap-2">
                        {item.leadId ? (
                          <Button variant="secondary">
                            <Link href={`/nsa/leads/${item.leadId}`}>
                              <Link2 className="mr-2 h-4 w-4" />
                              Open lead
                            </Link>
                          </Button>
                        ) : null}
                        {item.normalizedDomain ? <Badge>{item.normalizedDomain}</Badge> : null}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
          </CardContent>
        </Card>
        </div>

        <Card>
        <CardHeader>
          <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
            <div>
              <CardTitle>Lead list</CardTitle>
              <CardDescription>Search by company or domain, then open the detail view to inspect source provenance and job history.</CardDescription>
            </div>
            <div className="flex flex-col gap-3 sm:flex-row">
              <Input
                value={searchInput}
                onChange={(event) => setSearchInput(event.target.value)}
                placeholder="Search company or domain"
                className="sm:w-72"
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    event.preventDefault();
                    applySearch(searchInput);
                  }
                }}
              />
              <Button
                variant="secondary"
                onClick={() => {
                  applySearch(searchInput);
                }}
              >
                Search
              </Button>
            </div>
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            {statusFilters.map((filter) => (
              <Button
                key={filter.value}
                type="button"
                variant={statusFilter === filter.value ? "default" : "secondary"}
                onClick={() => applyStatus(filter.value)}
              >
                {filter.label}
              </Button>
            ))}
            <Button
              type="button"
              variant="ghost"
              onClick={() => {
                setSearchInput("");
                setQuery("");
                setStatusFilter("all");
                setPage(1);
                syncUrl({ q: "", status: "all", page: 1 });
              }}
            >
              Clear filters
            </Button>
            <Button type="button" variant="ghost" onClick={refreshList}>
              Refresh
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <LoadingState label="Loading leads..." />
          ) : items.length === 0 ? (
            <EmptyState
              title="No leads yet"
              description="Import a CSV or create the first lead manually. The list will populate here once the intake endpoints are used."
            />
          ) : (
            <>
                {mergedRecords > 0 ? (
                  <div className="mb-4 rounded-2xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
                    <div className="flex items-start gap-3">
                      <Merge className="mt-0.5 h-4 w-4 shrink-0" />
                      <div>
                        <div className="font-medium">Merged records on this page</div>
                        <div className="mt-1 text-xs leading-5 text-amber-100/80">
                        Versioned leads indicate a duplicate-domain merge or later operator edits. Open the detail view to inspect preserved source refs and the latest job that touched the record.
                        </div>
                      </div>
                    </div>
                  </div>
                ) : null}

              <div className="overflow-hidden rounded-2xl border border-line">
                <div className="grid grid-cols-[1.4fr_1.1fr_0.7fr_0.8fr_0.9fr_0.7fr] gap-3 border-b border-line bg-panel-2 px-4 py-3 text-xs uppercase tracking-[0.16em] text-muted">
                  <div>Company</div>
                  <div>Website</div>
                  <div>Status</div>
                  <div>Latest job</div>
                  <div>Missing</div>
                  <div>Actions</div>
                </div>
                <div className="divide-y divide-line">
                  {items.map((lead: LeadListItem) => (
                    <div key={lead.id} className="grid grid-cols-[1.4fr_1.1fr_0.7fr_0.8fr_0.9fr_0.7fr] gap-3 px-4 py-4 text-sm">
                      <div>
                        <div className="font-medium text-text">{lead.companyName || "Missing company name"}</div>
                        <div className="mt-1 flex flex-wrap gap-2">
                          <Badge>{lead.sourceType}</Badge>
                          <Badge>{lead.normalizedDomain}</Badge>
                          {lead.version > 1 ? (
                            <Badge className="border-amber-500/40 bg-amber-500/10 text-amber-100">
                              <Merge className="mr-1 h-3.5 w-3.5" />
                              Merged
                            </Badge>
                          ) : null}
                        </div>
                      </div>
                      <div className="break-all text-muted">{lead.websiteUrl}</div>
                      <div>
                        <Badge className={lead.status === "needs_review" ? "border-amber-500/40 bg-amber-500/10 text-amber-100" : ""}>
                          {statusLabel(lead.status)}
                        </Badge>
                        <div className="mt-2 text-xs text-muted">v{lead.version}</div>
                      </div>
                      <div>
                        {lead.latestJob ? (
                          <div className="space-y-2">
                            <Badge>{jobLabel(lead.latestJob.status)}</Badge>
                            <LeadProgress progress={lead.latestJob.progress} label={lead.latestJob.step} />
                          </div>
                        ) : (
                          <span className="text-xs text-muted">No job yet</span>
                        )}
                      </div>
                      <div className="flex flex-wrap gap-1">
                        {lead.missingFields.length ? (
                          lead.missingFields.map((field) => (
                            <Badge key={field} className="border-amber-500/40 bg-amber-500/10 text-amber-100">
                              {field}
                            </Badge>
                          ))
                        ) : (
                          <span className="text-xs text-muted">None</span>
                        )}
                      </div>
                      <div className="flex flex-col items-start gap-2">
                        <Button variant="secondary">
                          <Link href={`/nsa/leads/${lead.id}`}>Open</Link>
                        </Button>
                        <Button type="button" variant="ghost" onClick={() => void archiveSelectedLead(lead.id)}>
                          Archive
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="mt-4 flex flex-col gap-3 border-t border-line pt-4 text-sm text-muted sm:flex-row sm:items-center sm:justify-between">
                <div>
                  Showing {startItem}-{endItem} of {data.pagination.total} leads
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    type="button"
                    variant="secondary"
                    disabled={currentPage <= 1}
                    onClick={() => {
                      const nextPage = Math.max(1, currentPage - 1);
                      setPage(nextPage);
                      syncUrl({ page: nextPage });
                    }}
                  >
                    Previous
                  </Button>
                  <span className="min-w-24 text-center text-xs uppercase tracking-[0.2em] text-muted">
                    Page {currentPage} of {totalPages}
                  </span>
                  <Button
                    type="button"
                    variant="secondary"
                    disabled={currentPage >= totalPages || data.pagination.total === 0}
                    onClick={() => {
                      const nextPage = Math.min(totalPages, currentPage + 1);
                      setPage(nextPage);
                      syncUrl({ page: nextPage });
                    }}
                  >
                    Next
                  </Button>
                </div>
              </div>
            </>
          )}
        </CardContent>
        </Card>
      </PageFrame>
    </>
  );
}
