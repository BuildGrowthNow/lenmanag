"use client";

import { useEffect, useState } from "react";

import { MessageDraftsWorkspace } from "@/components/message-drafts-workspace";
import { PageFrame } from "@/components/shell/page-frame";
import { getLead, getLeadMasterBrief, listLeads } from "@/lib/api/leads";
import { getVariantsForLead } from "@/lib/api/sites";
import { listMessageDrafts } from "@/lib/api/messages";
import type { GeneratedSite, LeadDetail, MasterBrief, MessageDraft } from "@/lib/types";

type MessageLeadSummary = {
  lead: LeadDetail;
  brief: MasterBrief | null;
  site: GeneratedSite | null;
  drafts: MessageDraft[];
};

export default function MessagesPage() {
  const [leadSummaries, setLeadSummaries] = useState<MessageLeadSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;

    async function loadData() {
      try {
        const leads = await listLeads({ limit: 200 });
        const summaries = await Promise.all(
          leads.items.map(async (lead) => {
            const [detail, brief, variants, drafts] = await Promise.all([
              getLead(lead.id),
              getLeadMasterBrief(lead.id),
              getVariantsForLead(lead.id),
              listMessageDrafts(lead.id),
            ]);
            if (!detail) return null;
            const site = variants[0] ?? null;
            return { lead: detail, brief, site, drafts: drafts.items };
          })
        );
        if (mounted) {
          setLeadSummaries(
            summaries.filter((e): e is NonNullable<typeof e> => e !== null)
          );
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
      description="Draft, review, and send outreach for published leads. Drafts stay tied to the approved brief and generated preview."
    >
      {loading ? (
        <div className="text-sm text-muted">Loading leads…</div>
      ) : (
        <MessageDraftsWorkspace leadSummaries={leadSummaries} />
      )}
    </PageFrame>
  );
}
