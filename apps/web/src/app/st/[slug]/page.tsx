/**
 * Preview shell page for AI-generated compiled sites.
 * Dynamically loads and mounts compiled bundles with brand tokens.
 * Accessed via public URLs: /st/{slug}
 */

import { Suspense } from 'react';
import { notFound } from 'next/navigation';
import { PreviewRenderer } from './preview-renderer';

interface PageProps {
  params: Promise<{ slug: string }>;
}

async function fetchSiteBundle(slug: string) {
  const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
  const res = await fetch(`${apiUrl}/api/v1/public/st/${slug}`, {
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
  const { slug } = await params;
  const site = await fetchSiteBundle(slug);

  if (!site) {
    notFound();
  }

  // Resolve the HTML content — prefer staticHtml, fall back to sourceCode for refined sites
  const htmlContent = site.staticHtml || (site.sourceCode?.trimStart().startsWith('<') ? site.sourceCode : null);

  if (htmlContent) {
    return <div dangerouslySetInnerHTML={{ __html: htmlContent }} />;
  }

  // Check if this is a compiled Next.js bundle
  const isCompiledBundle = !!site.compiledBundleUrl;

  if (!isCompiledBundle) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-zinc-950 text-zinc-50">
        <div className="text-center space-y-4">
          <h1 className="text-2xl font-semibold">Not compiled yet</h1>
          <p className="text-zinc-400">
            This site is still being processed. Check back shortly.
          </p>
          <p className="text-sm text-zinc-500">Slug: {slug}</p>
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
        slug={slug}
        bundleUrl={site.compiledBundleUrl}
        brandTokens={site.brandTokens}
        compilationStatus={site.compilationStatus}
      />
    </Suspense>
  );
}
