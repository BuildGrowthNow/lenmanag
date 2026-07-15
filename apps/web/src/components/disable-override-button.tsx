"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { disableSiteOverride } from "@/lib/api/sites";
import { Button } from "@/components/ui/button";

type DisableOverrideButtonProps = {
  siteId: string;
  overrideId: string;
};

export function DisableOverrideButton({ siteId, overrideId }: DisableOverrideButtonProps) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleDisable() {
    setBusy(true);
    setError(null);
    try {
      await disableSiteOverride(siteId, overrideId);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to disable override.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-2">
      <Button type="button" variant="ghost" disabled={busy} onClick={() => void handleDisable()}>
        {busy ? "Disabling..." : "Disable override"}
      </Button>
      {error ? <div className="text-xs text-destructive">{error}</div> : null}
    </div>
  );
}
