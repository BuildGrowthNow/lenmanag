import { PageFrame } from "@/components/shell/page-frame";
import { QueueHealthPanel } from "@/components/queue-health-panel";
import { getQueueHealth } from "@/lib/api/jobs";

export default async function ScalePage() {
  const health = await getQueueHealth();

  return (
    <PageFrame
      eyebrow="Scale & automation"
      title="Queue health and retries"
      description="Live Celery queue health so operators can retry failed jobs, monitor stalled crawls, and keep high-volume imports flowing."
    >
      <QueueHealthPanel health={health} />
    </PageFrame>
  );
}
