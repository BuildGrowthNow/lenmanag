import { PageFrame } from "@/components/shell/page-frame";
import { SiteReviewQueue } from "@/components/site-review-queue";
import { getSiteReviewQueue } from "@/lib/api/sites";

export default async function ReviewQueuePage({ searchParams }: { searchParams?: Promise<{ offset?: string }> }) {
  const resolvedSearchParams = searchParams ? await searchParams : undefined;
  const rawOffset = resolvedSearchParams?.offset;
  const numericOffset = rawOffset ? Number(rawOffset) : 0;
  const queue = await getSiteReviewQueue({ limit: 25, offset: Number.isFinite(numericOffset) ? numericOffset : 0 });

  return (
    <PageFrame
      eyebrow="QA"
      title="Browser review queue"
      description="Screenshot-backed review workflow with diversity checks, regeneration controls, and automation handoff visibility."
    >
      <SiteReviewQueue queue={queue} />
    </PageFrame>
  );
}
