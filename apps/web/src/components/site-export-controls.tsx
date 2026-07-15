"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertCircle, CheckCircle, Clock } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { downloadSiteBundle, recordSiteExport } from "@/lib/api/sites";
import { ExportSyncModal } from "@/components/export-sync-modal";
import type { SiteExportMetadata, SiteExportRecord, SiteOverrideRecord } from "@/lib/types";

const EXPORT_TYPES = [
  { value: "local_bundle", label: "Local bundle" },
  { value: "github", label: "GitHub repo" },
  { value: "zip", label: "Zip handoff" }
];

type SiteExportControlsProps = {
  siteId: string;
  previewSlug: string;
  exportMetadata: SiteExportMetadata | null | undefined;
  history: SiteExportRecord[];
};

export function SiteExportControls({ siteId, previewSlug, exportMetadata, history }: SiteExportControlsProps) {
  const router = useRouter();
  const [busy, setBusy] = useState<"record" | "download" | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [showSyncModal, setShowSyncModal] = useState(false);
  const [form, setForm] = useState({
    exportType: exportMetadata?.exportType || "local_bundle",
    repoUrl: exportMetadata?.repoUrl || "",
    branch: exportMetadata?.branch || "",
    commitSha: exportMetadata?.commitSha || "",
    exportPath: exportMetadata?.exportPath || `${previewSlug}-bundle.zip`,
    notes: exportMetadata?.notes || ""
  });

  function updateField(field: keyof typeof form, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  function handleSyncSuccess(overrides: SiteOverrideRecord[]) {
    setMessage(`Synced ${overrides.length} local edits as structured overrides.`);
    router.refresh();
  }

  async function handleRecord(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy("record");
    setMessage(null);
    try {
      await recordSiteExport(siteId, {
        exportType: form.exportType,
        repoUrl: form.repoUrl || null,
        branch: form.branch || null,
        commitSha: form.commitSha || null,
        exportPath: form.exportPath || null,
        notes: form.notes || null
      });
      setMessage("Export metadata saved.");
      router.refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to save export metadata.");
    } finally {
      setBusy(null);
    }
  }

  async function handleDownload() {
    setBusy("download");
    setMessage(null);
    try {
      const { blob, filename } = await downloadSiteBundle(siteId);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      setMessage("Bundle downloaded.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to download bundle.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-4">
      {/* Sync status indicator */}
      {exportMetadata && exportMetadata.exportSyncStatus === "out_of_sync" && (
        <div className="rounded-2xl border border-rose-500/30 bg-rose-500/5 p-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="mt-0.5 h-5 w-5 text-rose-400" />
            <div className="flex-1">
              <div className="font-medium text-rose-100">Export out of sync</div>
              <div className="mt-1 text-sm text-rose-200/80">
                Local edits have been made to the exported bundle. Sync these edits back to structured overrides to ensure they survive regeneration.
              </div>
              <Button
                type="button"
                variant="secondary"
                className="mt-3"
                onClick={() => setShowSyncModal(true)}
              >
                Sync Local Edits
              </Button>
            </div>
          </div>
        </div>
      )}

      <form onSubmit={handleRecord} className="space-y-3">
        <div className="grid gap-3 md:grid-cols-2">
          <label className="space-y-1 text-sm text-muted">
            <span>Export type</span>
            <select
              className="w-full rounded-xl border border-line bg-panel px-3 py-2 text-sm text-text"
              value={form.exportType}
              onChange={(event) => updateField("exportType", event.target.value)}
              disabled={busy === "record"}
            >
              {EXPORT_TYPES.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label className="space-y-1 text-sm text-muted">
            <span>Repo URL / destination</span>
            <Input value={form.repoUrl} onChange={(event) => updateField("repoUrl", event.target.value)} placeholder="https://github.com/lenquant/site" disabled={busy === "record"} />
          </label>
          <label className="space-y-1 text-sm text-muted">
            <span>Branch</span>
            <Input value={form.branch} onChange={(event) => updateField("branch", event.target.value)} placeholder="main" disabled={busy === "record"} />
          </label>
          <label className="space-y-1 text-sm text-muted">
            <span>Commit SHA</span>
            <Input value={form.commitSha} onChange={(event) => updateField("commitSha", event.target.value)} placeholder="abc123" disabled={busy === "record"} />
          </label>
          <label className="space-y-1 text-sm text-muted">
            <span>Export filename / path</span>
            <Input value={form.exportPath} onChange={(event) => updateField("exportPath", event.target.value)} placeholder={`${previewSlug}-bundle.zip`} disabled={busy === "record"} />
          </label>
        </div>
        <label className="space-y-1 text-sm text-muted">
          <span>Notes</span>
          <Textarea value={form.notes} onChange={(event) => updateField("notes", event.target.value)} rows={3} disabled={busy === "record"} />
        </label>
        <div className="flex flex-wrap gap-3">
          <Button type="submit" disabled={busy === "record"}>
            {busy === "record" ? "Saving..." : "Record export"}
          </Button>
          <Button type="button" variant="secondary" onClick={handleDownload} disabled={busy === "download"}>
            {busy === "download" ? "Preparing bundle..." : "Download static bundle"}
          </Button>
        </div>
      </form>
      {exportMetadata ? (
        <div className="rounded-2xl border border-line bg-panel-2 p-4 text-sm text-muted">
          <div className="flex items-center justify-between">
            <div>Last export: {new Date(exportMetadata.updatedAt).toLocaleString()}</div>
            <div className="flex items-center gap-2">
              {exportMetadata.exportSyncStatus === "synced" && (
                <div className="flex items-center gap-1 text-emerald-400">
                  <CheckCircle className="h-4 w-4" />
                  <span className="text-xs">Synced</span>
                </div>
              )}
              {exportMetadata.exportSyncStatus === "out_of_sync" && (
                <div className="flex items-center gap-1 text-rose-400">
                  <AlertCircle className="h-4 w-4" />
                  <span className="text-xs">Out of sync</span>
                </div>
              )}
              {exportMetadata.exportSyncStatus === "needs_review" && (
                <div className="flex items-center gap-1 text-amber-400">
                  <Clock className="h-4 w-4" />
                  <span className="text-xs">Needs review</span>
                </div>
              )}
            </div>
          </div>
          {exportMetadata.exportPath ? <div>Path: {exportMetadata.exportPath}</div> : null}
          {exportMetadata.repoUrl ? <div>Destination: {exportMetadata.repoUrl}</div> : null}
          {exportMetadata.lastSyncedAt ? <div>Last synced: {new Date(exportMetadata.lastSyncedAt).toLocaleString()}</div> : null}
        </div>
      ) : (
        <div className="text-sm text-muted">No export has been recorded yet. Use the form above to log a bundle handoff.</div>
      )}
      <div className="space-y-2 rounded-2xl border border-line bg-panel-2 p-4">
        <div className="text-xs uppercase tracking-[0.18em] text-muted">Export history</div>
        {history.length ? (
          <div className="space-y-2">
            {history.map((record) => (
              <div key={record.id} className="rounded-xl border border-line/50 bg-panel px-3 py-2 text-sm text-text">
                <div className="font-medium">{record.exportType}</div>
                <div className="text-xs text-muted">{new Date(record.createdAt).toLocaleString()}</div>
                {record.repoUrl ? <div className="text-xs text-muted">Destination: {record.repoUrl}</div> : null}
                {record.notes ? <div className="text-xs text-muted">Notes: {record.notes}</div> : null}
              </div>
            ))}
          </div>
        ) : (
          <div className="text-sm text-muted">No export history yet.</div>
        )}
      </div>
      {message ? <div className="text-sm text-accentText/80">{message}</div> : null}

      {/* Export Sync Modal */}
      {exportMetadata && (
        <ExportSyncModal
          siteId={siteId}
          exportId={exportMetadata.exportType || "default"}
          isOpen={showSyncModal}
          onClose={() => setShowSyncModal(false)}
          onSuccess={handleSyncSuccess}
        />
      )}
    </div>
  );
}
