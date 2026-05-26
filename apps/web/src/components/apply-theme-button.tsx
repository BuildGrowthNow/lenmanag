"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { createSiteOverride } from "@/lib/api/sites";
import { Button } from "@/components/ui/button";

type Props = {
  siteId: string;
  themeKey: string;
  themeName?: string;
};

export function ApplyThemeButton({ siteId, themeKey, themeName }: Props) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function handleApply() {
    setBusy(true);
    setMessage(null);
    try {
      await createSiteOverride(siteId, {
        scope: "brand",
        path: "themeKey",
        value: themeKey,
        previousValue: null,
        reason: `Operator selected theme ${themeName ?? themeKey}`,
      });
      setMessage("Theme applied.");
      router.refresh();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not apply theme.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mt-3">
      <Button onClick={() => void handleApply()} disabled={busy}>
        {busy ? "Applying..." : "Apply theme"}
      </Button>
      {message ? <div className="mt-2 text-xs text-muted">{message}</div> : null}
    </div>
  );
}
