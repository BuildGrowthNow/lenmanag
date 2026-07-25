"use client";

import Link from "next/link";
import { Archive, Plus, Upload, RefreshCw } from "lucide-react";
import { Suspense, useCallback, useEffect, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { Button, buttonVariants } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { EmptyState } from "@/components/state/empty-state";
import { ErrorState } from "@/components/state/error-state";
import { LoadingState } from "@/components/state/loading-state";
import { PageFrame } from "@/components/shell/page-frame";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { archiveLead, createLead, importLeads, listLeads } from "@/lib/api/leads";
import type { LeadImportResponse, LeadListItem, LeadListResponse, PipelineMode, PipelineStage, GenerationType } from "@/lib/types";
import { cn } from "@/lib/utils";

const PAGE_SIZE = 25;

// ── Pipeline stage display ─────────────────────────────────────────────────

const STAGE_LABEL: Record<PipelineStage, string> = {
  new: "New",
  extracting: "Extracting",
  extracted: "Extracted",
  briefing: "Briefing",
  brief_ready: "Brief ready",
  generating: "Generating",
  qa: "QA",
  ready: "Ready",
  published: "Published",
  needs_attention: "Needs attention",
  archived: "Archived",
};

function stageBadgeClass(stage: PipelineStage): string {
  switch (stage) {
    case "extracting":
    case "extracted":
      return "border-blue-500/40 bg-blue-500/10 text-blue-200";
    case "briefing":
    case "brief_ready":
      return "border-yellow-500/40 bg-yellow-500/10 text-yellow-200";
    case "generating":
    case "qa":
      return "border-purple-500/40 bg-purple-500/10 text-purple-200";
    case "ready":
      return "border-emerald-500/40 bg-emerald-500/10 text-emerald-200";
    case "published":
      return "border-emerald-400/60 bg-emerald-400/15 text-emerald-100 font-semibold";
    case "needs_attention":
      return "border-rose-500/40 bg-rose-500/10 text-rose-200";
    case "archived":
      return "border-white/10 bg-white/5 text-muted";
    default:
      return "border-white/15 bg-white/5 text-muted";
  }
}

const ANIMATED_STAGES: Set<PipelineStage> = new Set(["extracting", "briefing", "generating"]);

function StageBadge({ stage }: { stage: PipelineStage }) {
  const isAnimated = ANIMATED_STAGES.has(stage);
  return (
    <Badge
      className={cn(
        stageBadgeClass(stage),
        isAnimated && "animate-pulse"
      )}
    >
      {STAGE_LABEL[stage]}
    </Badge>
  );
}

// ── Relative time ─────────────────────────────────────────────────────────

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

// ── Source label ──────────────────────────────────────────────────────────

function sourceLabel(source: string): string {
  if (source === "csv") return "CSV";
  if (source === "manual") return "Manual";
  if (source === "crm") return "CRM";
  return "API";
}

// ── URL state sync ────────────────────────────────────────────────────────

function parsePage(value: string | null) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed < 1) return 1;
  return Math.floor(parsed);
}

function LeadUrlStateSync({
  onChange,
}: {
  onChange: (s: { q: string; stage: PipelineStage | "all"; page: number }) => void;
}) {
  const searchParams = useSearchParams();
  useEffect(() => {
    const stage = searchParams.get("stage");
    const validStages: Array<PipelineStage | "all"> = [
      "all", "new", "extracting", "extracted", "briefing", "brief_ready",
      "generating", "qa", "ready", "published", "needs_attention",
    ];
    onChange({
      q: searchParams.get("q") ?? "",
      stage: (validStages.includes(stage as PipelineStage) ? stage : "all") as PipelineStage | "all",
      page: parsePage(searchParams.get("page")),
    });
  }, [onChange, searchParams]);
  return null;
}

// ── Add Lead modal ────────────────────────────────────────────────────────

type AddLeadModalProps = {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
};

const GENERATION_TYPE_OPTIONS: { key: GenerationType; label: string; description: string }[] = [
  { key: "html_v1", label: "HTML V1 - Professional", description: "Clean, corporate design with subtle gradients" },
  { key: "html_v2", label: "HTML V2 - Bold", description: "Bold startup aesthetic with vibrant colors" },
  { key: "html_v3", label: "HTML V3 - Creative", description: "Creative direction with unique layouts" },
  { key: "nextjs", label: "Next.js Site", description: "Full React-based site with components" },
];

function AddLeadModal({ open, onClose, onCreated }: AddLeadModalProps) {
  const [form, setForm] = useState({ companyName: "", contactName: "", websiteUrl: "", notes: "" });
  const [mode, setMode] = useState<PipelineMode>("auto");
  const [generationTypes, setGenerationTypes] = useState<GenerationType[]>(["nextjs"]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setForm({ companyName: "", contactName: "", websiteUrl: "", notes: "" });
      setMode("auto");
      setGenerationTypes(["nextjs"]);
      setError(null);
    }
  }, [open]);

  function toggleGenerationType(type: GenerationType) {
    setGenerationTypes(prev => {
      if (prev.includes(type)) {
        return prev.filter(t => t !== type);
      }
      return [...prev, type];
    });
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await createLead({
        companyName: form.companyName.trim() || null,
        contactName: form.contactName.trim() || null,
        websiteUrl: form.websiteUrl.trim(),
        notes: form.notes.trim() || null,
        pipelineMode: mode,
        generationTypes: generationTypes.length > 0 ? generationTypes : ["nextjs"],
      });
      onCreated();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create lead.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Add lead</DialogTitle>
        </DialogHeader>
        <form className="space-y-4" onSubmit={handleSubmit}>
          <div className="space-y-1.5">
            <label className="text-xs uppercase tracking-[0.2em] text-muted">Website URL *</label>
            <Input
              required
              value={form.websiteUrl}
              onChange={(e) => setForm((f) => ({ ...f, websiteUrl: e.target.value }))}
              placeholder="https://example.com"
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs uppercase tracking-[0.2em] text-muted">Company name</label>
            <Input
              value={form.companyName}
              onChange={(e) => setForm((f) => ({ ...f, companyName: e.target.value }))}
              placeholder="Optional — extracted automatically if blank"
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs uppercase tracking-[0.2em] text-muted">Contact name</label>
            <Input
              value={form.contactName}
              onChange={(e) => setForm((f) => ({ ...f, contactName: e.target.value }))}
              placeholder="Optional — shown on the redesign preview page"
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs uppercase tracking-[0.2em] text-muted">Mode</label>
            <div className="flex gap-2">
              {(["auto", "manual"] as PipelineMode[]).map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => setMode(m)}
                  className={cn(
                    "flex-1 rounded-xl border px-3 py-2 text-sm transition",
                    mode === m
                      ? "border-accent/60 bg-accent/10 text-accent"
                      : "border-line text-muted hover:border-white/20 hover:text-text"
                  )}
                >
                  <div className="font-medium capitalize">{m}</div>
                  <div className="mt-0.5 text-xs opacity-70">
                    {m === "auto"
                      ? "Runs all steps automatically"
                      : "Pauses at brief and QA for approval"}
                  </div>
                </button>
              ))}
            </div>
          </div>
          <div className="space-y-1.5">
            <label className="text-xs uppercase tracking-[0.2em] text-muted">Site Variants</label>
            <div className="grid grid-cols-2 gap-2">
              {GENERATION_TYPE_OPTIONS.map((opt) => (
                <button
                  key={opt.key}
                  type="button"
                  onClick={() => toggleGenerationType(opt.key)}
                  className={cn(
                    "rounded-xl border px-3 py-2 text-left text-sm transition",
                    generationTypes.includes(opt.key)
                      ? "border-accent/60 bg-accent/10 text-accent"
                      : "border-line text-muted hover:border-white/20 hover:text-text"
                  )}
                >
                  <div className="flex items-center gap-2">
                    <div className={cn(
                      "h-4 w-4 rounded border flex items-center justify-center",
                      generationTypes.includes(opt.key)
                        ? "border-accent bg-accent"
                        : "border-line"
                    )}>
                      {generationTypes.includes(opt.key) && (
                        <svg className="h-3 w-3 text-background" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                        </svg>
                      )}
                    </div>
                    <span className="font-medium">{opt.label}</span>
                  </div>
                  <div className="mt-0.5 text-xs opacity-70 pl-6">{opt.description}</div>
                </button>
              ))}
            </div>
            {generationTypes.length === 0 && (
              <p className="text-xs text-amber-400">Select at least one variant type</p>
            )}
          </div>
          <div className="space-y-1.5">
            <button
              type="button"
              className="text-xs text-muted hover:text-text"
              onClick={(e) => {
                const target = e.currentTarget.nextElementSibling as HTMLElement;
                if (target) target.style.display = target.style.display === "none" ? "block" : "none";
              }}
            >
              Add notes ▾
            </button>
            <div style={{ display: "none" }}>
              <Textarea
                value={form.notes}
                onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
                placeholder="Any context worth preserving"
                rows={3}
              />
            </div>
          </div>
          {error ? <p className="text-sm text-rose-400">{error}</p> : null}
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={onClose}>Cancel</Button>
            <Button type="submit" disabled={saving}>
              {saving ? "Adding…" : "Add lead"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ── CSV Import modal ──────────────────────────────────────────────────────

type ImportModalProps = {
  open: boolean;
  onClose: () => void;
  onImported: () => void;
};

function ImportModal({ open, onClose, onImported }: ImportModalProps) {
  const [mode, setMode] = useState<PipelineMode>("auto");
  const [file, setFile] = useState<File | null>(null);
  const [saving, setSaving] = useState(false);
  const [result, setResult] = useState<LeadImportResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setFile(null);
      setResult(null);
      setError(null);
    }
  }, [open]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setSaving(true);
    setError(null);
    try {
      const res = await importLeads(file, mode);
      setResult(res);
      onImported();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import failed.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Import CSV</DialogTitle>
        </DialogHeader>
        {result ? (
          <div className="space-y-4">
            <div className="rounded-2xl border border-line bg-panel-2 p-4 text-sm">
              <div className="grid grid-cols-3 gap-3 text-center">
                <div>
                  <div className="text-2xl font-semibold text-emerald-300">{result.createdCount}</div>
                  <div className="text-xs text-muted">Created</div>
                </div>
                <div>
                  <div className="text-2xl font-semibold text-amber-300">{result.mergedCount}</div>
                  <div className="text-xs text-muted">Merged</div>
                </div>
                <div>
                  <div className="text-2xl font-semibold text-rose-300">{result.failedCount}</div>
                  <div className="text-xs text-muted">Failed</div>
                </div>
              </div>
            </div>
            {result.failedCount > 0 ? (
              <div className="space-y-1.5 text-sm">
                <div className="text-xs uppercase tracking-[0.18em] text-muted">Failed rows</div>
                {result.items.filter((i) => i.status === "failed").map((item) => (
                  <div key={item.rowNumber} className="rounded-xl border border-rose-500/20 bg-rose-500/5 px-3 py-2 text-xs text-rose-300">
                    Row {item.rowNumber}: {item.message}
                  </div>
                ))}
              </div>
            ) : null}
            <DialogFooter>
              <Button onClick={onClose}>Done</Button>
            </DialogFooter>
          </div>
        ) : (
          <form className="space-y-4" onSubmit={handleSubmit}>
            <div className="space-y-1.5">
              <label className="text-xs uppercase tracking-[0.2em] text-muted">CSV file</label>
              <Input
                type="file"
                accept=".csv,text/csv"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
              <p className="text-xs text-muted">
                Columns: <code>companyName</code>, <code>websiteUrl</code>. Aliases: <code>company</code>, <code>website</code>, <code>url</code>, <code>domain</code>.
              </p>
            </div>
            <div className="space-y-1.5">
              <label className="text-xs uppercase tracking-[0.2em] text-muted">Mode (applied to all)</label>
              <div className="flex gap-2">
                {(["auto", "manual"] as PipelineMode[]).map((m) => (
                  <button
                    key={m}
                    type="button"
                    onClick={() => setMode(m)}
                    className={cn(
                      "flex-1 rounded-xl border px-3 py-2 text-sm transition",
                      mode === m
                        ? "border-accent/60 bg-accent/10 text-accent"
                        : "border-line text-muted hover:border-white/20 hover:text-text"
                    )}
                  >
                    <div className="font-medium capitalize">{m}</div>
                  </button>
                ))}
              </div>
            </div>
            {error ? <p className="text-sm text-rose-400">{error}</p> : null}
            <DialogFooter>
              <Button type="button" variant="ghost" onClick={onClose}>Cancel</Button>
              <Button type="submit" disabled={saving || !file}>
                {saving ? "Importing…" : `Import${file ? ` "${file.name}"` : ""}`}
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}

// ── Pipeline summary strip ─────────────────────────────────────────────────

type SummaryChipProps = {
  label: string;
  count: number;
  active: boolean;
  color: string;
  onClick: () => void;
};

function SummaryChip({ label, count, active, color, onClick }: SummaryChipProps) {
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

// ── Main page ─────────────────────────────────────────────────────────────

type StageFilter = PipelineStage | "all";

export default function LeadsPage() {
  const router = useRouter();
  const pathname = usePathname();
  const [q, setQ] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [stageFilter, setStageFilter] = useState<StageFilter>("all");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<LeadListResponse>({
    items: [],
    pagination: { total: 0, limit: PAGE_SIZE, offset: 0 },
    pipelineSummary: null,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshSeed, setRefreshSeed] = useState(0);
  const [showAdd, setShowAdd] = useState(false);
  const [showImport, setShowImport] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const handleUrlStateChange = useCallback(
    (s: { q: string; stage: StageFilter; page: number }) => {
      setQ(s.q);
      setSearchInput(s.q);
      setStageFilter(s.stage);
      setPage(s.page);
    },
    []
  );

  const syncUrl = useCallback(
    (next: { q?: string; stage?: StageFilter; page?: number }) => {
      const params = new URLSearchParams();
      const nq = next.q ?? q;
      const ns = next.stage ?? stageFilter;
      const np = next.page ?? page;
      if (nq) params.set("q", nq);
      if (ns && ns !== "all") params.set("stage", ns);
      if (np > 1) params.set("page", String(np));
      const suffix = params.toString();
      router.replace(suffix ? `${pathname}?${suffix}` : pathname, { scroll: false });
    },
    [page, pathname, q, router, stageFilter]
  );

  useEffect(() => {
    let active = true;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const offset = (page - 1) * PAGE_SIZE;
        const result = await listLeads({
          q: q || undefined,
          stage: stageFilter !== "all" ? stageFilter : undefined,
          limit: PAGE_SIZE,
          offset,
        });
        if (!active) return;
        setData(result);
        const totalPages = Math.max(1, Math.ceil(result.pagination.total / PAGE_SIZE));
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
    return () => { active = false; };
  }, [page, q, stageFilter, refreshSeed, syncUrl]);

  function refresh() {
    setRefreshSeed((s) => s + 1);
  }

  function applySearch(next: string) {
    const t = next.trim();
    setQ(t);
    setPage(1);
    syncUrl({ q: t, page: 1 });
  }

  function applyStage(next: StageFilter) {
    setStageFilter(next);
    setPage(1);
    syncUrl({ stage: next, page: 1 });
  }

  async function handleArchive(id: string) {
    setActionMessage(null);
    try {
      await archiveLead(id);
      setActionMessage("Lead archived.");
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not archive lead.");
    }
  }

  const items = data.items;

  const summary = data.pipelineSummary;
  const totalPages = Math.max(1, Math.ceil(data.pagination.total / PAGE_SIZE));
  const startItem = data.pagination.total === 0 ? 0 : data.pagination.offset + 1;
  const endItem = Math.min(data.pagination.offset + items.length, data.pagination.total);

  const summaryChips: Array<{ key: StageFilter; label: string; count: number; color: string }> = [
    { key: "extracting", label: "Processing", count: summary?.processing ?? 0, color: "blue" },
    { key: "needs_attention", label: "Needs attention", count: summary?.needs_attention ?? 0, color: "rose" },
    { key: "brief_ready", label: "Brief ready", count: summary?.brief_ready ?? 0, color: "yellow" },
    { key: "qa", label: "Site generated", count: summary?.site_generated ?? 0, color: "purple" },
    { key: "ready", label: "Ready to publish", count: summary?.ready_to_publish ?? 0, color: "emerald" },
    { key: "published", label: "Published", count: summary?.published ?? 0, color: "emerald" },
  ];

  return (
    <>
      <Suspense fallback={null}>
        <LeadUrlStateSync onChange={handleUrlStateChange} />
      </Suspense>

      <AddLeadModal
        open={showAdd}
        onClose={() => setShowAdd(false)}
        onCreated={() => { refresh(); setActionMessage("Lead added and extraction started."); }}
      />
      <ImportModal
        open={showImport}
        onClose={() => setShowImport(false)}
        onImported={() => { refresh(); setActionMessage("Import complete."); }}
      />

      <PageFrame
        eyebrow="Pipeline"
        title="Leads"
        description="Every lead moves automatically from extraction through site generation. Intervene only when the pipeline flags a blocker."
      >
        {/* Top bar actions */}
        <div className="flex items-center justify-between gap-3">
          <div />
          <div className="flex items-center gap-2">
            <Button variant="secondary" onClick={() => setShowImport(true)}>
              <Upload className="mr-2 h-4 w-4" />
              Import CSV
            </Button>
            <Button onClick={() => setShowAdd(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Add Lead
            </Button>
          </div>
        </div>

        {/* Pipeline summary strip */}
        {summary ? (
          <div className="flex flex-wrap gap-2">
            {summaryChips.map((chip) => (
              <SummaryChip
                key={chip.key}
                label={chip.label}
                count={chip.count}
                active={stageFilter === chip.key}
                color={chip.color}
                onClick={() => applyStage(stageFilter === chip.key ? "all" : chip.key)}
              />
            ))}
          </div>
        ) : null}

        {error ? <ErrorState title="Failed to load leads" description={error} /> : null}
        {actionMessage ? (
          <div className="rounded-2xl border border-line bg-panel px-4 py-3 text-sm text-text">
            {actionMessage}
            <button type="button" className="ml-3 text-xs text-muted hover:text-text" onClick={() => setActionMessage(null)}>
              ✕
            </button>
          </div>
        ) : null}

        {/* Filters + search */}
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-wrap items-center gap-2">
            <Button
              type="button"
              variant={stageFilter === "all" ? "default" : "secondary"}
              onClick={() => applyStage("all")}
            >
              All
            </Button>
            {(["extracting", "needs_attention", "brief_ready", "qa", "ready", "published"] as StageFilter[]).map((s) => (
              <Button
                key={s}
                type="button"
                variant={stageFilter === s ? "default" : "secondary"}
                onClick={() => applyStage(s)}
              >
                {STAGE_LABEL[s as PipelineStage]}
              </Button>
            ))}
            {stageFilter !== "all" ? (
              <Button type="button" variant="ghost" onClick={() => applyStage("all")}>
                Clear
              </Button>
            ) : null}
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
                  applySearch(searchInput);
                }
              }}
            />
            <Button variant="secondary" onClick={() => applySearch(searchInput)}>
              Search
            </Button>
            <Button variant="ghost" onClick={refresh}>
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Table */}
        {loading ? (
          <LoadingState label="Loading leads…" />
        ) : items.length === 0 ? (
          <EmptyState
            title={stageFilter !== "all" ? `No leads in "${STAGE_LABEL[stageFilter as PipelineStage]}"` : "No leads yet"}
            description="Add a lead or import a CSV to start the pipeline."
            action={
              <Button onClick={() => setShowAdd(true)}>
                <Plus className="mr-2 h-4 w-4" />
                Add Lead
              </Button>
            }
          />
        ) : (
          <>
            <div className="overflow-hidden rounded-2xl border border-line">
              {/* Header */}
              <div className="grid grid-cols-[2fr_1.2fr_1.5fr_0.8fr_0.9fr_0.8fr] gap-3 border-b border-line bg-panel-2 px-4 py-3 text-xs uppercase tracking-[0.16em] text-muted">
                <div>Company</div>
                <div>Stage</div>
                <div>Status</div>
                <div>Source</div>
                <div>Added</div>
                <div>Actions</div>
              </div>
              {/* Rows */}
              <div className="divide-y divide-line">
                {items.map((lead: LeadListItem) => (
                  <LeadRow key={lead.id} lead={lead} onArchive={handleArchive} />
                ))}
              </div>
            </div>

            {/* Pagination */}
            <div className="flex items-center justify-between gap-3 text-sm text-muted">
              <span>Showing {startItem}–{endItem} of {data.pagination.total}</span>
              <div className="flex items-center gap-2">
                <Button
                  variant="secondary"
                  disabled={page <= 1}
                  onClick={() => { const p = page - 1; setPage(p); syncUrl({ page: p }); }}
                >
                  Previous
                </Button>
                <span className="min-w-20 text-center text-xs uppercase tracking-[0.2em]">
                  {page} / {totalPages}
                </span>
                <Button
                  variant="secondary"
                  disabled={page >= totalPages}
                  onClick={() => { const p = page + 1; setPage(p); syncUrl({ page: p }); }}
                >
                  Next
                </Button>
              </div>
            </div>
          </>
        )}
      </PageFrame>
    </>
  );
}

// ── Lead row ──────────────────────────────────────────────────────────────

function LeadRow({ lead, onArchive }: { lead: LeadListItem; onArchive: (id: string) => void }) {
  const statusDetail = lead.pipelineStatusDetail ?? lead.latestJob?.step ?? null;

  return (
    <div className="grid grid-cols-[2fr_1.2fr_1.5fr_0.8fr_0.9fr_0.8fr] gap-3 px-4 py-4 text-sm hover:bg-white/2">
      {/* Company */}
      <div>
        <Link href={`/app/leads/${lead.id}`} className="font-medium text-text hover:text-accent transition-colors">
          {lead.companyName || <span className="text-muted italic">No name</span>}
        </Link>
        <div className="mt-1 text-xs text-muted">{lead.normalizedDomain}</div>
      </div>
      {/* Stage */}
      <div className="flex items-start pt-0.5">
        <StageBadge stage={lead.pipelineStage} />
      </div>
      {/* Status detail */}
      <div className="flex items-start pt-1 text-xs text-muted">
        {statusDetail ?? <span className="italic">—</span>}
      </div>
      {/* Source */}
      <div className="flex items-start pt-1 text-xs text-muted">
        {sourceLabel(lead.sourceType)}
      </div>
      {/* Added */}
      <div className="flex items-start pt-1 text-xs text-muted">
        {relativeTime(lead.createdAt)}
      </div>
      {/* Actions */}
      <div className="flex items-start gap-1 pt-0.5">
        <Link href={`/app/leads/${lead.id}`} className={buttonVariants({ variant: "secondary", size: "sm" })}>View</Link>
        <Button
          variant="ghost"
          onClick={() => onArchive(lead.id)}
          title="Archive"
        >
          <Archive className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  );
}
