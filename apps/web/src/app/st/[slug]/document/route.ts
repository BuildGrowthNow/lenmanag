import { NextResponse } from 'next/server';

export async function GET(
  _request: Request,
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
  return new NextResponse(html, {
    headers: {
      'Content-Type': 'text/html; charset=utf-8',
      'Cache-Control': 'no-store',
      'X-LenManag-Static-Document': 'true',
    },
  });
}
