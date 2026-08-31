/**
 * Core compilation logic for AI-generated TSX components.
 * Uses esbuild for fast, reliable compilation.
 */

import * as esbuild from 'esbuild';
import postcss from 'postcss';
import tailwindcss from 'tailwindcss';
import { validateTsxSource, sanitizeComponentName } from './validate.js';
import { createVirtualModulesPlugin } from './virtual-modules-plugin.js';

export interface CompileRequest {
  sourceCode: string;
  componentName: string;
  siteId: string;
}

export interface CompileResult {
  success: boolean;
  bundleCode?: string;
  cssCode?: string;
  error?: string;
  validationErrors?: string[];
}

/**
 * Compile TSX source code to executable JavaScript bundle.
 * Returns both JS bundle and extracted CSS.
 */
export async function compileTsx(request: CompileRequest): Promise<CompileResult> {
  const { sourceCode, componentName, siteId } = request;

  // Validate source code first
  const validation = validateTsxSource(sourceCode);
  if (!validation.valid) {
    return {
      success: false,
      error: 'Source code validation failed',
      validationErrors: validation.errors,
    };
  }

  const safeName = sanitizeComponentName(componentName);

  try {
    // Build with esbuild
    const result = await esbuild.build({
      stdin: {
        contents: sourceCode,
        loader: 'tsx',
        resolveDir: process.cwd(),
        sourcefile: `${safeName}.tsx`,
      },
      bundle: true,
      format: 'iife',
      globalName: 'LandingPageBundle',
      target: 'es2020',
      jsx: 'automatic',
      jsxImportSource: 'react',
      write: false,
      minify: true,
      sourcemap: false,
      // External: only React runtime (loaded via CDN in preview shell)
      // All other libraries (framer-motion, lucide-react, gsap, etc.) will be bundled
      external: [
        'react',
        'react-dom',
        'react/jsx-runtime',
        'react/jsx-dev-runtime',
      ],
      banner: {
        js: [
          `var React = window.React;`,
          `var ReactDOM = window.ReactDOM;`,
          `var require = (function() {`,
          `  var m = {'react': window.React, 'react-dom': window.ReactDOM, 'react/jsx-runtime': window.__reactJsxRuntime, 'react/jsx-dev-runtime': window.__reactJsxRuntime};`,
          `  return function(id) { if (m[id]) return m[id]; throw new Error('Module not found: ' + id); };`,
          `})();`,
        ].join(' '),
      },
      footer: {
        js: `if (typeof LandingPageBundle !== 'undefined') { window.LandingPageBundle = LandingPageBundle; }`,
      },
      // Enable tree-shaking and code splitting for optimal bundle size
      treeShaking: true,
      plugins: [createVirtualModulesPlugin()],
      logLevel: 'silent',
      metafile: true,
    });

    if (!result.outputFiles || result.outputFiles.length === 0) {
      return {
        success: false,
        error: 'Compilation produced no output',
      };
    }

    // Extract JS and CSS
    let bundleCode = '';
    let cssCode = '';

    for (const file of result.outputFiles) {
      const text = new TextDecoder().decode(file.contents);
      if (file.path.endsWith('.css')) {
        cssCode += text;
      } else {
        bundleCode += text;
      }
    }

    if (!bundleCode) {
      return {
        success: false,
        error: 'No JavaScript bundle generated',
      };
    }

    // Generated TSX is not part of the web app's Tailwind content globs. Build
    // a stylesheet from this exact source so arbitrary, responsive, hover,
    // and animation utilities are deterministic per site.
    const generatedCss = await postcss([
      tailwindcss({
        content: [{ raw: sourceCode, extension: 'tsx' }],
        corePlugins: { preflight: true },
        theme: { extend: {} },
      }),
    ]).process('@tailwind base;\n@tailwind components;\n@tailwind utilities;', { from: `${safeName}.css` });

    return {
      success: true,
      bundleCode,
      cssCode: `${generatedCss.css}\n${cssCode}`,
    };
  } catch (err: any) {
    const errorMessage = err?.message || String(err);

    // Parse esbuild errors for better feedback
    let friendlyError = errorMessage;
    if (err?.errors && Array.isArray(err.errors)) {
      const messages = err.errors.map((e: any) =>
        `${e.text} (${e.location?.file}:${e.location?.line}:${e.location?.column})`
      ).join('\n');
      friendlyError = messages || errorMessage;
    }

    return {
      success: false,
      error: `Compilation failed: ${friendlyError}`,
    };
  }
}

/**
 * Helper to check if esbuild is available.
 */
export function isCompilerAvailable(): boolean {
  try {
    return !!esbuild.version;
  } catch {
    return false;
  }
}
