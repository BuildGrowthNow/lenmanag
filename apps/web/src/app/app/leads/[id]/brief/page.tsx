/**
 * Master Brief Review & Approval Page
 * Shows AI-generated master brief for review and approval before site generation.
 */

import { notFound } from 'next/navigation';
import { BriefReviewClient } from './brief-review-client';
import { getMasterBrief } from '@/lib/api/master-brief';

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function MasterBriefPage({ params }: PageProps) {
  const { id: leadId } = await params;

  // Fetch master brief
  const brief = await getMasterBrief(leadId);

  if (!brief) {
    notFound();
  }

  return <BriefReviewClient leadId={leadId} initialBrief={brief} />;
}
