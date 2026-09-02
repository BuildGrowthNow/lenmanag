/**
 * Preview shell page for AI-generated compiled sites.
 * Dynamically loads and mounts compiled bundles with brand tokens.
 * Accessed via public URLs: /st/{slug}
 */

import { Suspense } from 'react';
import { notFound } from 'next/navigation';
import { PreviewRenderer } from './preview-renderer';
import { isPreviewUsable } from '@/lib/api/sites';

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

  // Resolve the HTML content — prefer staticHtml, fall back to sourceCode for refined sites.
  // Refined sites may have a stray 'use client'; directive prepended to the HTML — strip it.
  const rawSource: string = site.staticHtml || site.sourceCode || '';
  const strippedSource = rawSource.replace(/^['"]use client['"];\s*/s, '').trimStart();
  const htmlContent = strippedSource.startsWith('<') ? strippedSource : null;

  const isStaticVariant = site.variantType === 'html_v1' || site.variantType === 'html_v2' || site.variantType === 'html_v3';

  if (isStaticVariant && htmlContent && isPreviewUsable(site)) {
    return (
      <iframe
        title={`Generated preview for ${slug}`}
        src={`/st/${encodeURIComponent(slug)}/document`}
        className="min-h-screen w-full border-0"
        style={{ height: '100vh' }}
      />
    );
  }

  // Check if this is a compiled Next.js bundle
  const isCompiledBundle = isPreviewUsable(site) && !!site.compiledBundleUrl;

  if (!isCompiledBundle) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-zinc-950 text-zinc-50">
        <div className="text-center space-y-4">
          <h1 className="text-2xl font-semibold">Preview unavailable</h1>
          <p className="text-zinc-400">
            This variant did not produce a usable published artifact. No website was published.
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
        cssUrl={site.compiledCssUrl}
        brandTokens={site.brandTokens}
        compilationStatus={site.compilationStatus}
      />
    </Suspense>
  );
}
