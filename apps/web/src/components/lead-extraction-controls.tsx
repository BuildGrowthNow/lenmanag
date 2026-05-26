"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { refreshLeadExtraction, startLeadExtraction } from "@/lib/api/leads";
import type { ExtractionSnapshot } from "@/lib/types";

type LeadExtractionControlsProps = {
  leadId: string;
  extraction: ExtractionSnapshot | null;
};

export function LeadExtractionControls({ leadId, extraction }: LeadExtractionControlsProps) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const hasCrawlHistory = extraction ? extraction.version > 0 : false;

  async function triggerExtraction(mode: "start" | "refresh") {
    setBusy(true);
    setMessage(null);
    try {
      const result =
        mode === "refresh" && hasCrawlHistory ? await refreshLeadExtraction(leadId) : await startLeadExtraction(leadId);
      setMessage(`${result.job.step}. ${result.extraction.pagesCrawled} page(s) crawled.`);
      router.refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Failed to start extraction.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-3">
        <Button type="button" onClick={() => void triggerExtraction(hasCrawlHistory ? "refresh" : "start")} disabled={busy}>
          {busy ? "Working..." : hasCrawlHistory ? "Refresh crawl" : "Start crawl"}
        </Button>
        {hasCrawlHistory ? (
          <Button type="button" variant="secondary" onClick={() => void triggerExtraction("start")} disabled={busy}>
            Run another crawl
          </Button>
        ) : null}
      </div>
      {message ? <div className="text-xs leading-5 text-muted">{message}</div> : null}
    </div>
  );
}

