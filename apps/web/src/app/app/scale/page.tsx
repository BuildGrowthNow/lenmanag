import { PageFrame } from "@/components/shell/page-frame";
import { QueueHealthPanel } from "@/components/queue-health-panel";
import { getQueueHealth } from "@/lib/api/jobs";

export default async function ScalePage() {
  const health = await getQueueHealth();

  return (
    <PageFrame
      eyebrow="Ops"
      title="Queue health"
      description="Monitor Celery job queue health, retry failed jobs, and kill stalled crawls. Auto-refresh every 30 seconds is available."
    >
      <QueueHealthPanel health={health} />
    </PageFrame>
  );
}
