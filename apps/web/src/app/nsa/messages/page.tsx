import { MessageDraftsWorkspace } from "@/components/message-drafts-workspace";
import { PageFrame } from "@/components/shell/page-frame";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getLead, getLeadBrief, listLeads } from "@/lib/api/leads";
import { getSite } from "@/lib/api/sites";
import { listMessageDrafts } from "@/lib/api/messages";

export default async function MessagesPage() {
  const leads = await listLeads({ limit: 50 });
  const leadSummaries = await Promise.all(
    leads.items.map(async (lead) => {
      const [detail, brief, site, drafts] = await Promise.all([getLead(lead.id), getLeadBrief(lead.id), getSite(lead.id), listMessageDrafts(lead.id)]);
      if (!detail) {
        return null;
      }
      return { lead: detail, brief, site, drafts: drafts.items };
    })
  );

  const typedLeadSummaries = leadSummaries.filter((entry): entry is NonNullable<typeof entry> => entry !== null);

  const readyCount = typedLeadSummaries.reduce((count, entry) => count + entry.drafts.filter((draft) => draft.status === "ready").length, 0);
  const editedCount = typedLeadSummaries.reduce((count, entry) => count + entry.drafts.filter((draft) => draft.status === "edited").length, 0);
  const totalDrafts = typedLeadSummaries.reduce((count, entry) => count + entry.drafts.length, 0);

  return (
    <PageFrame
      eyebrow="Messages"
      title="Outreach drafts"
      description="Channel-specific drafts stay tied to the approved brief, the generated preview, and the handoff metadata."
    >
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardDescription>Drafts</CardDescription>
            <CardTitle className="text-3xl">{totalDrafts}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Edited</CardDescription>
            <CardTitle className="text-3xl">{editedCount}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Ready</CardDescription>
            <CardTitle className="text-3xl">{readyCount}</CardTitle>
          </CardHeader>
        </Card>
      </div>

      <MessageDraftsWorkspace leadSummaries={typedLeadSummaries} />
    </PageFrame>
  );
}

