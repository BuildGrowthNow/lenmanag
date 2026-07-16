import { MessageDraftsWorkspace } from "@/components/message-drafts-workspace";
import { PageFrame } from "@/components/shell/page-frame";
import { getLead, getLeadBrief, listLeads } from "@/lib/api/leads";
import { getSite } from "@/lib/api/sites";
import { listMessageDrafts } from "@/lib/api/messages";

export default async function MessagesPage() {
  const leads = await listLeads({ limit: 50 });
  const leadSummaries = await Promise.all(
    leads.items.map(async (lead) => {
      const [detail, brief, site, drafts] = await Promise.all([
        getLead(lead.id),
        getLeadBrief(lead.id),
        getSite(lead.id),
        listMessageDrafts(lead.id),
      ]);
      if (!detail) return null;
      return { lead: detail, brief, site, drafts: drafts.items };
    })
  );

  const typedSummaries = leadSummaries.filter(
    (entry): entry is NonNullable<typeof entry> => entry !== null
  );

  return (
    <PageFrame
      eyebrow="Outreach"
      title="Messages"
      description="Draft, review, and send outreach for published leads. Drafts stay tied to the approved brief and generated preview."
    >
      <MessageDraftsWorkspace leadSummaries={typedSummaries} />
    </PageFrame>
  );
}
