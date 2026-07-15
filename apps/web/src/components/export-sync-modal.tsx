"use client";

import { useState } from "react";
import { CheckCircle, XCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { syncExportEdits } from "@/lib/api/sites";
import type { SiteOverrideRecord } from "@/lib/types";

type ExportSyncModalProps = {
  siteId: string;
  exportId: string;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (overrides: SiteOverrideRecord[]) => void;
};

type LocalEdit = {
  id: string;
  path: string;
  value: string;
  reason: string;
  selected: boolean;
};

export function ExportSyncModal({ siteId, exportId, isOpen, onClose, onSuccess }: ExportSyncModalProps) {
  const [edits, setEdits] = useState<LocalEdit[]>([
    { id: "1", path: "", value: "", reason: "", selected: true }
  ]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  function addEdit() {
    setEdits([...edits, { id: String(edits.length + 1), path: "", value: "", reason: "", selected: true }]);
  }

  function removeEdit(id: string) {
    setEdits(edits.filter((edit) => edit.id !== id));
  }

  function updateEdit(id: string, field: keyof LocalEdit, value: string | boolean) {
    setEdits(edits.map((edit) => (edit.id === id ? { ...edit, [field]: value } : edit)));
  }

  async function handleSync() {
    setBusy(true);
    setMessage(null);
    try {
      const selectedEdits = edits.filter((edit) => edit.selected && edit.path && edit.value);
      if (selectedEdits.length === 0) {
        setMessage("Please select at least one edit to sync.");
        setBusy(false);
        return;
      }

      const payload = selectedEdits.map((edit) => ({
        path: edit.path,
        value: edit.value,
        reason: edit.reason || "Local edit synced from export"
      }));

      const overrides = await syncExportEdits(siteId, exportId, payload);
      onSuccess(overrides);
      onClose();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to sync edits.");
    } finally {
      setBusy(false);
    }
  }

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-2xl rounded-2xl border border-line bg-panel p-6 shadow-lg">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-text">Sync Local Edits</h2>
          <Button variant="ghost" onClick={onClose} disabled={busy}>
            <XCircle className="h-5 w-5" />
          </Button>
        </div>

        <div className="mb-4 text-sm text-muted">
          Select the local edits you want to sync back to structured overrides. These edits will survive regeneration.
        </div>

        <div className="space-y-3">
          {edits.map((edit) => (
            <div key={edit.id} className="rounded-xl border border-line bg-panel-2 p-4">
              <div className="mb-3 flex items-center justify-between">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={edit.selected}
                    onChange={(e) => updateEdit(edit.id, "selected", e.target.checked)}
                    className="h-4 w-4 rounded border-line bg-panel"
                  />
                  <span className="text-sm font-medium text-text">Edit #{edit.id}</span>
                </label>
                {edits.length > 1 && (
                  <Button variant="ghost" onClick={() => removeEdit(edit.id)} disabled={busy}>
                    Remove
                  </Button>
                )}
              </div>
              <div className="space-y-2">
                <Input
                  placeholder="Path (e.g., hero.headline)"
                  value={edit.path}
                  onChange={(e) => updateEdit(edit.id, "path", e.target.value)}
                  disabled={busy}
                />
                <Textarea
                  placeholder="Value"
                  value={edit.value}
                  onChange={(e) => updateEdit(edit.id, "value", e.target.value)}
                  rows={2}
                  disabled={busy}
                />
                <Input
                  placeholder="Reason (optional)"
                  value={edit.reason}
                  onChange={(e) => updateEdit(edit.id, "reason", e.target.value)}
                  disabled={busy}
                />
              </div>
            </div>
          ))}
        </div>

        <Button type="button" variant="secondary" onClick={addEdit} disabled={busy} className="mt-3 w-full">
          Add another edit
        </Button>

        {message && (
          <div className="mt-4 rounded-xl border border-line/50 bg-panel-2 p-3 text-sm text-muted">
            {message}
          </div>
        )}

        <div className="mt-6 flex justify-end gap-3">
          <Button variant="secondary" onClick={onClose} disabled={busy}>
            Cancel
          </Button>
          <Button onClick={handleSync} disabled={busy}>
            {busy ? "Syncing..." : "Sync selected edits"}
          </Button>
        </div>
      </div>
    </div>
  );
}
