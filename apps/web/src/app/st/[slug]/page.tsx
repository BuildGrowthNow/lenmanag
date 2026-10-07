/**
 * Preview shell page for AI-generated compiled sites.
 * Dynamically loads and mounts compiled bundles with brand tokens.
 * Accessed via public URLs: /st/{slug}
 */

import { notFound } from 'next/navigation';

interface PageProps {
  params: Promise<{ slug: string }>;
}

function hasPreviewArtifact(site: Record<string, unknown>): boolean {
  if (!["success", "completed"].includes(String(site.compilationStatus ?? ""))) return false;
  if (site.variantType === "html_v1" || site.variantType === "html_v2" || site.variantType === "html_v3") {
    return typeof site.staticHtml === "string" && Boolean(site.staticHtml.trim());
  }
  return typeof site.compiledBundleUrl === "string" && Boolean(site.compiledBundleUrl.trim());
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
  const hasArtifact = hasPreviewArtifact(site as Record<string, unknown>);

  if (isStaticVariant && htmlContent && hasArtifact) {
    return (
      <iframe
        title={`Generated preview for ${slug}`}
        src={`/st/${encodeURIComponent(slug)}/document`}
      className="min-h-screen w-full border-0"
      style={{ height: '100vh' }}
      sandbox="allow-scripts"
      referrerPolicy="no-referrer"
    />
    );
  }

  // Compiled model output is rendered in a separate sandboxed document. The
  // route below fetches the artifact server-side and mounts it only inside the
  // isolated frame, keeping generated code out of this preview shell.
  const isCompiledBundle = hasArtifact && !!site.compiledBundleUrl;

  if (!isCompiledBundle) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-zinc-950 text-zinc-50">
        <div className="text-center space-y-4">
          <h1 className="text-2xl font-semibold">Preview unavailable</h1>
          <p className="text-zinc-400">
            This variant has no generated artifact to preview yet. QA approval is still required before publication.
          </p>
          <p className="text-sm text-zinc-500">Slug: {slug}</p>
        </div>
      </div>
    );
  }

  return (
    <iframe
      title={`Generated preview for ${slug}`}
      src={`/st/${encodeURIComponent(slug)}/compiled`}
      className="min-h-screen w-full border-0"
      style={{ height: '100vh' }}
      sandbox="allow-scripts"
      referrerPolicy="no-referrer"
    />
  );
}
