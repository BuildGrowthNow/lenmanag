import { PageFrame, PlaceholderPanel } from "@/components/shell/page-frame";

export default function AnalyticsPage() {
  return (
    <PageFrame
      eyebrow="Analytics"
      title="Operational analytics"
      description="This surface will later show preview visits, CTA clicks, outbound link activity, and admin action tracking."
    >
      <PlaceholderPanel title="Analytics pipeline not wired" description="The dashboard layout is in place, but event ingestion and rollups arrive in later phases." />
    </PageFrame>
  );
}

