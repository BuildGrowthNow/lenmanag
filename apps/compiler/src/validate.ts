/**
 * Validation utilities for AI-generated TSX code.
 * Ensures generated code is safe to compile and execute.
 */

export interface ValidationResult {
  valid: boolean;
  errors: string[];
}

export const APPROVED_IMPORTS = new Set([
  'react', 'react-dom', 'react/jsx-runtime', 'react/jsx-dev-runtime',
  'framer-motion', 'gsap', 'gsap/ScrollTrigger', 'lenis',
  'embla-carousel-react', 'lucide-react', 'clsx', 'tailwind-merge',
  'three', '@react-three/fiber', '@react-three/drei',
  '@radix-ui/react-dialog', '@radix-ui/react-dropdown-menu', '@radix-ui/react-separator',
  '@radix-ui/react-slot', '@radix-ui/react-tabs', '@radix-ui/react-tooltip',
]);

export function validateDeclaredImports(source: string, declared: string[] = []): ValidationResult {
  const errors: string[] = [];
  const allowed = new Set(declared.filter((dependency) => APPROVED_IMPORTS.has(dependency)));
  for (const dependency of declared) {
    if (!APPROVED_IMPORTS.has(dependency) && !dependency.startsWith('@/')) {
      errors.push(`Capability is not allowlisted: ${dependency}`);
    }
  }
  for (const match of source.matchAll(/(?:import|from)\s+['"]([^'"]+)['"]/g)) {
    const name = match[1];
    if (name.startsWith('@/components/ui/') || name === '@/lib/utils') continue;
    if (!APPROVED_IMPORTS.has(name)) errors.push(`Import is not allowlisted: ${name}`);
    else if (!allowed.has(name)) errors.push(`Import is not declared: ${name}`);
  }
  return { valid: errors.length === 0, errors };
}

export function validateDeclaredCapabilityUsage(source: string, declared: string[] = []): ValidationResult {
  const errors: string[] = [];
  for (const dependency of declared) {
    if (!dependency || dependency.startsWith('@/')) continue;
    const escaped = dependency.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    if (!new RegExp(`(?:import|from)\\s+['"]${escaped}['"]`).test(source)) {
      errors.push(`Declared capability is unused: ${dependency}`);
    }
  }
  return { valid: errors.length === 0, errors };
}

export function extractImportedDependencies(source: string, candidates: string[] = []): string[] {
  return candidates.filter((dependency) =>
    new RegExp(`(?:import|from)\\s+['"]${dependency.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}['"]`).test(source)
  );
}

export function validateCapabilityFallback(
  dependencies: string[] = [],
  webglFallback = false,
): ValidationResult {
  const usesWebgl = dependencies.some((dependency) =>
    ['three', '@react-three/fiber', '@react-three/drei'].includes(dependency)
  );
  return usesWebgl && !webglFallback
    ? { valid: false, errors: ['Three.js capability requires an explicit 2D fallback'] }
    : { valid: true, errors: [] };
}

/**
 * Validate TSX source code for safety and correctness.
 * Checks for dangerous imports, forbidden APIs, and structural issues.
 */
export function validateTsxSource(source: string, declared: string[] = []): ValidationResult {
  const errors: string[] = [];
  errors.push(...validateDeclaredImports(source, declared).errors);

  // Check for dangerous imports
  const dangerousImports = [
    /import\s+.*\s+from\s+['"]fs['"]/,
    /import\s+.*\s+from\s+['"]node:fs['"]/,
    /import\s+.*\s+from\s+['"]child_process['"]/,
    /import\s+.*\s+from\s+['"]node:child_process['"]/,
    /import\s+.*\s+from\s+['"]http[s]?['"]/,
    /import\s+.*\s+from\s+['"]node:http[s]?['"]/,
    /import\s+.*\s+from\s+['"]net['"]/,
    /import\s+.*\s+from\s+['"]node:net['"]/,
  ];

  for (const pattern of dangerousImports) {
    if (pattern.test(source)) {
      errors.push(`Dangerous import detected: ${pattern.source}`);
    }
  }

  // Check for external URL imports
  if (/import\s+.*\s+from\s+['"]https?:\/\//.test(source)) {
    errors.push('External URL imports are not allowed');
  }

  // Check for relative imports outside component
  if (/import\s+.*\s+from\s+['"]\.\.[\/\\]/.test(source)) {
    errors.push('Relative imports outside current directory are not allowed');
  }

  // Check for forbidden global APIs
  const forbiddenApis = [
    /\beval\s*\(/,
    /\bFunction\s*\(/,
    /\bfetch\s*\(/,
    /\bXMLHttpRequest\b/,
    /\bWebSocket\b/,
  ];

  for (const pattern of forbiddenApis) {
    if (pattern.test(source)) {
      errors.push(`Forbidden API usage detected: ${pattern.source}`);
    }
  }

  // Check for inline script tags
  if (/<script[^>]*>/i.test(source)) {
    errors.push('Inline <script> tags are not allowed');
  }

  // Keep browser artifacts aligned with the static generator's content and
  // security contract.  These checks are intentionally deterministic so a
  // provider cannot bypass them by changing its prompt.
  if (source.includes('—')) {
    errors.push('Visible content must not contain an em dash');
  }
  if (/\b(?:Arial|Comic\s+Sans(?:\s+MS)?)\b/i.test(source)) {
    errors.push('Prohibited basic Windows font detected');
  }
  if (/\b(?:lorem ipsum|example\.com|TODO|XXX|coming soon|contact us for details|image placeholder)\b/i.test(source)) {
    errors.push('Placeholder content detected');
  }
  if (/(?:src|href)\s*=\s*['"]http:\/\//i.test(source) || /url\(\s*['"]?http:\/\//i.test(source)) {
    errors.push('Insecure HTTP asset URL detected');
  }

  // Check for default export (required)
  if (!/export\s+default\s+/.test(source)) {
    errors.push('Component must have a default export');
  }

  // Basic JSX structure check
  if (!/<[A-Z]/.test(source) && !/<div|<span|<section|<main/.test(source)) {
    errors.push('Component must return valid JSX');
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}

/**
 * Sanitize component name to be filesystem-safe.
 */
export function sanitizeComponentName(name: string): string {
  return name
    .replace(/[^a-zA-Z0-9-_]/g, '-')
    .replace(/^-+|-+$/g, '')
    .substring(0, 50);
}
