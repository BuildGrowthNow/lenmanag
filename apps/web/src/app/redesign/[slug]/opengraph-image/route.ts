import { NextResponse } from "next/server";

interface RouteContext {
  params: Promise<{ slug: string }>;
}

export const dynamic = "force-dynamic";
export const revalidate = 0;

export async function GET(_request: Request, { params }: RouteContext) {
  const { slug } = await params;
  const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

  try {
    const redesignResponse = await fetch(
      `${apiUrl}/api/v1/public/redesign/${encodeURIComponent(slug)}`,
      { cache: "no-store" },
    );
    if (!redesignResponse.ok) {
      return new NextResponse("Preview image unavailable", { status: 404 });
    }

    const envelope = await redesignResponse.json();
    const data = envelope.data;
    const imageUrl = data?.variants?.[0]?.screenshotUrl || data?.logoUrl;
    if (typeof imageUrl !== "string" || !imageUrl) {
      return new NextResponse("Preview image unavailable", { status: 404 });
    }

    const imageResponse = await fetch(imageUrl, { cache: "no-store" });
    if (!imageResponse.ok || !imageResponse.body) {
      return new NextResponse("Preview image unavailable", { status: 404 });
    }

    const headers = new Headers();
    headers.set("Content-Type", imageResponse.headers.get("content-type") || "image/jpeg");
    headers.set("Cache-Control", "public, max-age=3600, s-maxage=86400");
    headers.set("Content-Disposition", "inline");
    return new Response(imageResponse.body, { headers });
  } catch {
    return new NextResponse("Preview image unavailable", { status: 404 });
  }
}
