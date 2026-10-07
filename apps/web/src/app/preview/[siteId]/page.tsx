/**
 * Preview shell page for AI-generated compiled sites.
 * Dynamically loads and mounts compiled bundles with brand tokens.
 */

import { Suspense } from 'react';
import { notFound } from 'next/navigation';
import { PreviewRenderer } from './preview-renderer';

interface PageProps {
  params: Promise<{ siteId: string }>;
}

async function fetchSiteBundle(siteId: string) {
  const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
  const res = await fetch(`${apiUrl}/api/v1/public/st/${siteId}`, {
    cache: 'no-store',
  });

  if (!res.ok) {
    if (res.status === 404) return null;
    throw new Error(`Failed to fetch site: ${res.status}`);
  }

  const envelope = await res.json();
  return envelope.data;
}

export default async function PreviewPage({ params }: PageProps) {
  const { siteId } = await params;
  const site = await fetchSiteBundle(siteId);

  if (!site) {
    notFound();
  }

  // Check if this is a compiled bundle or legacy JSON structure
  const isCompiledBundle = !!site.compiledBundleUrl;

  if (!isCompiledBundle) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-zinc-950 text-zinc-50">
        <div className="text-center space-y-4">
          <h1 className="text-2xl font-semibold">Legacy Site Format</h1>
          <p className="text-zinc-400">
            This site uses the legacy JSON format. It has not been compiled yet.
          </p>
          <p className="text-sm text-zinc-500">
            Site ID: {siteId}
          </p>
        </div>
      </div>
    );
  }

  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-zinc-950">
          <div className="animate-pulse text-zinc-400">Loading preview...</div>
        </div>
      }
    >
      <PreviewRenderer
        siteId={siteId}
        bundleUrl={site.compiledBundleUrl}
        brandTokens={site.brandTokens}
        compilationStatus={site.compilationStatus}
      />
    </Suspense>
  );
}
