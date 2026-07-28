"use client";

import { useEffect, useState } from "react";

import { MessageDraftsWorkspace } from "@/components/message-drafts-workspace";
import { PageFrame } from "@/components/shell/page-frame";
import { listLeads } from "@/lib/api/leads";
import { listMessageDrafts } from "@/lib/api/messages";
import type { LeadListItem, MessageDraft } from "@/lib/types";

type MessageLeadSummary = {
  lead: LeadListItem;
  brief: null;
  site: null;
  drafts: MessageDraft[];
};

const OUTREACH_STAGES = new Set(["qa", "ready", "published"]);

export default function MessagesPage() {
  const [leadSummaries, setLeadSummaries] = useState<MessageLeadSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;

    async function loadData() {
      try {
        const leadsResponse = await listLeads({ limit: 200 });
        const outreachLeads = leadsResponse.items.filter(
          (l) => OUTREACH_STAGES.has(l.pipelineStage)
        );
        const summaries = await Promise.all(
          outreachLeads.map(async (lead) => {
            const drafts = await listMessageDrafts(lead.id);
            return { lead, brief: null, site: null, drafts: drafts.items };
          })
        );
        if (mounted) {
          setLeadSummaries(summaries);
          setLoading(false);
        }
      } catch (error) {
        console.error("Failed to load leads:", error);
        if (mounted) setLoading(false);
      }
    }

    void loadData();
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <PageFrame
      eyebrow="Outreach"
      title="Messages"
      description="Draft, review, and send outreach for leads in QA, ready, and published stages."
    >
      {loading ? (
        <div className="text-sm text-muted">Loading leads…</div>
      ) : (
        <MessageDraftsWorkspace leadSummaries={leadSummaries} />
      )}
    </PageFrame>
  );
}
