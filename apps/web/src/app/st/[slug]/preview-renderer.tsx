'use client';

/**
 * Client-side renderer for compiled site bundles.
 * Loads the bundle, provides brand tokens context, and handles errors.
 */

import { useEffect, useState } from 'react';
import { ErrorBoundary } from 'react-error-boundary';

interface PreviewRendererProps {
  slug: string;
  bundleUrl: string;
  brandTokens?: any;
  compilationStatus?: string;
}

function ErrorFallback({ error }: { error: unknown }) {
  const errorMessage = error instanceof Error ? error.message : 'An unknown error occurred';

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
            {errorMessage}
          </pre>
        </div>
      </div>
    </div>
  );
}

export function PreviewRenderer({
  slug,
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

    const loadBundle = async () => {
      try {
        // Ensure React and JSX runtime are available globally for the bundle
        if (typeof window !== 'undefined') {
          const react = require('react');
          const reactDOM = require('react-dom');
          const jsxRuntime = require('react/jsx-runtime');
          (window as any).React = react;
          (window as any).ReactDOM = reactDOM;
          (window as any).__reactJsxRuntime = jsxRuntime;
        }

        // Fetch the IIFE bundle
        const response = await fetch(bundleUrl);
        if (!response.ok) {
          throw new Error(`Failed to fetch bundle: ${response.status}`);
        }
        const bundleCode = await response.text();

        // Create and inject script tag for IIFE bundle
        const script = document.createElement('script');
        script.textContent = bundleCode;
        document.head.appendChild(script);

        // The IIFE assigns to var LandingPageBundle AND our footer sets window.LandingPageBundle
        const bundle = (window as any).LandingPageBundle;
        if (!bundle) {
          throw new Error('Bundle loaded but LandingPageBundle not found on window');
        }

        // esbuild IIFE wraps exports: { default: Component, __esModule: true }
        const ResolvedComponent = bundle.default || bundle;
        if (typeof ResolvedComponent !== 'function') {
          throw new Error(
            `Bundle loaded but export is not a component (got ${typeof ResolvedComponent})`
          );
        }

        setComponent(() => ResolvedComponent);
        document.head.removeChild(script);
      } catch (err: unknown) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to load bundle';
        console.error('Failed to load bundle:', errorMessage);
        setLoadError(errorMessage);
      }
    };

    loadBundle();
  }, [bundleUrl, compilationStatus, slug]);

  if (loadError) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-zinc-950 text-zinc-50 p-8">
        <div className="max-w-md space-y-4 text-center">
          <h1 className="text-2xl font-semibold text-amber-400">
            Bundle Load Error
          </h1>
          <p className="text-zinc-400">{loadError}</p>
          <p className="text-xs text-zinc-600">Slug: {slug}</p>
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

    const root = document.documentElement;
    const propertiesToSet: Array<[string, string]> = [];

    if (tokens.primaryColor?.value) {
      propertiesToSet.push(['--brand-primary', tokens.primaryColor.value]);
    }
    if (tokens.secondaryColor?.value) {
      propertiesToSet.push(['--brand-secondary', tokens.secondaryColor.value]);
    }
    if (tokens.accentColor?.value) {
      propertiesToSet.push(['--brand-accent', tokens.accentColor.value]);
    }
    if (tokens.backgroundColor?.value) {
      propertiesToSet.push(['--brand-bg', tokens.backgroundColor.value]);
    }
    if (tokens.textColor?.value) {
      propertiesToSet.push(['--brand-text', tokens.textColor.value]);
    }
    if (tokens.borderColor?.value) {
      propertiesToSet.push(['--brand-border', tokens.borderColor.value]);
    }

    propertiesToSet.forEach(([property, value]) => {
      root.style.setProperty(property, value);
    });

    return () => {
      propertiesToSet.forEach(([property]) => {
        root.style.removeProperty(property);
      });
    };
  }, [tokens]);

  return <>{children}</>;
}
