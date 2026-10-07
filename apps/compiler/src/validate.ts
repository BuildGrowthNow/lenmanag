/**
 * Validation utilities for AI-generated TSX code.
 * Ensures generated code is safe to compile and execute.
 */

export interface ValidationResult {
  valid: boolean;
  errors: string[];
}

/**
 * Validate TSX source code for safety and correctness.
 * Checks for dangerous imports, forbidden APIs, and structural issues.
 */
export function validateTsxSource(source: string): ValidationResult {
  const errors: string[] = [];

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
