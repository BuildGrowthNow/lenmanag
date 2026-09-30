import { randomBytes } from 'node:crypto';
import { NextResponse } from 'next/server';

function nonceTrustedRuntime(html: string, nonce: string): string {
  return html
    .replace(
      /<(script|style)\b([^>]*\bdata-generated-site-(?:js|runtime|css)\b[^>]*)>/gi,
      (_match, tag: string, attrs: string) => {
        if (/\bnonce\s*=/.test(attrs)) return `<${tag}${attrs}>`;
        return `<${tag}${attrs} nonce="${nonce}">`;
      },
    );
}

export async function GET(
  request: Request,
  { params }: { params: Promise<{ slug: string }> },
) {
  const { slug } = await params;
  const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
  const response = await fetch(`${apiUrl}/api/v1/public/preview/${encodeURIComponent(slug)}`, {
    cache: 'no-store',
  });
  if (!response.ok) return new NextResponse('Site not found', { status: response.status });
  const html = await response.text();
  if (!html.trim()) return new NextResponse('Static document unavailable', { status: 409 });
  const nonce = randomBytes(18).toString('base64');
  const documentHtml = nonceTrustedRuntime(html, nonce);
  const backendOrigin = new URL(apiUrl, request.url).origin;
  const contentSecurityPolicy = [
    "default-src 'none'",
    `script-src 'nonce-${nonce}' ${backendOrigin}`,
    "script-src-attr 'none'",
    `style-src 'nonce-${nonce}' ${backendOrigin}`,
    'img-src https: data: blob:',
    'font-src https: data:',
    'media-src https: data: blob:',
    `form-action ${backendOrigin}`,
    "connect-src 'none'",
    "object-src 'none'",
    "base-uri 'none'",
    "frame-ancestors 'self'",
    'upgrade-insecure-requests',
  ].join('; ');
  return new NextResponse(documentHtml, {
    headers: {
      'Content-Type': 'text/html; charset=utf-8',
      'Cache-Control': 'no-store',
      'X-LenManag-Static-Document': 'true',
      'Permissions-Policy': 'camera=(), microphone=(), geolocation=()',
      'Content-Security-Policy': contentSecurityPolicy,
      'X-Content-Type-Options': 'nosniff',
    },
  });
}
