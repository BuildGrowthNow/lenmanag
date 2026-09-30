/**
 * Sandboxed document for compiled generated sites.
 * This route is intentionally loaded in an iframe with allow-scripts only.
 */

import { notFound } from 'next/navigation';
import { PreviewRenderer } from '../preview-renderer';
import { isPreviewUsable } from '@/lib/api/sites';

interface PageProps {
  params: Promise<{ slug: string }>;
}

async function fetchSite(slug: string) {
  const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
  const response = await fetch(`${apiUrl}/api/v1/public/st/${encodeURIComponent(slug)}`, {
    cache: 'no-store',
  });
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`Failed to fetch site: ${response.status}`);
  const envelope = await response.json();
  return envelope.data;
}

export default async function CompiledPreviewPage({ params }: PageProps) {
  const { slug } = await params;
  const site = await fetchSite(slug);
  if (!site || !isPreviewUsable(site) || !site.compiledBundleUrl) notFound();

  return (
    <PreviewRenderer
      slug={slug}
      bundleUrl={site.compiledBundleUrl}
      cssUrl={site.compiledCssUrl}
      brandTokens={site.brandTokens}
      compilationStatus={site.compilationStatus}
    />
  );
}
