'use client';

/**
 * Client-side renderer for compiled site bundles.
 * Loads the bundle, provides brand tokens context, and handles errors.
 */

import { useEffect, useState, Suspense, lazy } from 'react';
import { ErrorBoundary } from 'react-error-boundary';

interface PreviewRendererProps {
  siteId: string;
  bundleUrl: string;
  brandTokens?: any;
  compilationStatus?: string;
}

function ErrorFallback({ error }: { error: Error }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-950 text-zinc-50 p-8">
      <div className="max-w-2xl space-y-4">
        <div className="space-y-2">
          <h1 className="text-2xl font-semibold text-red-400">Render Error</h1>
          <p className="text-zinc-400">
            The site bundle failed to render. This may be due to:
          </p>
          <ul className="list-disc list-inside text-sm text-zinc-500 space-y-1">
            <li>Invalid component structure</li>
            <li>Missing dependencies</li>
            <li>Runtime JavaScript errors</li>
          </ul>
        </div>
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 overflow-auto">
          <pre className="text-xs text-red-400 whitespace-pre-wrap">
            {error.message}
          </pre>
        </div>
      </div>
    </div>
  );
}

export function PreviewRenderer({
  siteId,
  bundleUrl,
  brandTokens,
  compilationStatus,
}: PreviewRendererProps) {
  const [Component, setComponent] = useState<React.ComponentType | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    if (compilationStatus !== 'success' && compilationStatus !== 'completed') {
      setLoadError(
        `Site compilation is ${compilationStatus || 'pending'}. Cannot preview yet.`
      );
      return;
    }

    // Dynamically import the bundle
    const loadBundle = async () => {
      try {
        // For production bundles served from storage
        const bundleModule = await import(/* @vite-ignore */ bundleUrl);
        const DefaultExport = bundleModule.default;

        if (!DefaultExport) {
          throw new Error('Bundle has no default export');
        }

        setComponent(() => DefaultExport);
      } catch (err: any) {
        console.error('Failed to load bundle:', err);
        setLoadError(err?.message || 'Failed to load bundle');
      }
    };

    loadBundle();
  }, [bundleUrl, compilationStatus]);

  if (loadError) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-zinc-950 text-zinc-50 p-8">
        <div className="max-w-md space-y-4 text-center">
          <h1 className="text-2xl font-semibold text-amber-400">
            Bundle Load Error
          </h1>
          <p className="text-zinc-400">{loadError}</p>
          <p className="text-xs text-zinc-600">Site ID: {siteId}</p>
        </div>
      </div>
    );
  }

  if (!Component) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-zinc-950">
        <div className="animate-pulse text-zinc-400">Loading component...</div>
      </div>
    );
  }

  return (
    <ErrorBoundary FallbackComponent={ErrorFallback}>
      <BrandTokensProvider tokens={brandTokens}>
        <Component />
      </BrandTokensProvider>
    </ErrorBoundary>
  );
}

/**
 * Brand tokens context provider for AI-generated components.
 * Makes design tokens available to the compiled bundle.
 */
function BrandTokensProvider({
  tokens,
  children,
}: {
  tokens?: any;
  children: React.ReactNode;
}) {
  useEffect(() => {
    if (!tokens) return;

    // Inject brand tokens as CSS custom properties
    const root = document.documentElement;
    if (tokens.primaryColor?.value) {
      root.style.setProperty('--brand-primary', tokens.primaryColor.value);
    }
    if (tokens.secondaryColor?.value) {
      root.style.setProperty('--brand-secondary', tokens.secondaryColor.value);
    }
    if (tokens.accentColor?.value) {
      root.style.setProperty('--brand-accent', tokens.accentColor.value);
    }
    if (tokens.backgroundColor?.value) {
      root.style.setProperty('--brand-bg', tokens.backgroundColor.value);
    }
    if (tokens.textColor?.value) {
      root.style.setProperty('--brand-text', tokens.textColor.value);
    }
    if (tokens.borderColor?.value) {
      root.style.setProperty('--brand-border', tokens.borderColor.value);
    }
  }, [tokens]);

  return <>{children}</>;
}
