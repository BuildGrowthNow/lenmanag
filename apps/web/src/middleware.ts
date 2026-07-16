import { NextRequest, NextResponse } from "next/server";

export function middleware(request: NextRequest) {
  const host = request.headers.get("host") ?? "";

  // Public preview subdomain — always pass through, no auth check
  if (host.startsWith("sites.")) {
    return NextResponse.next();
  }

  const { pathname } = request.nextUrl;

  // Auth is JWT-based and stored in localStorage (client-side only).
  // The middleware can only gate routes at the server level using the
  // Authorization header (present on server-to-server calls). For
  // browser navigations the client-side layout handles the redirect.
  const hasAuthHeader = !!request.headers.get("authorization");

  // Allow access to auth pages without authentication
  if (pathname === "/login" || pathname === "/signup" || pathname === "/verify-email") {
    return NextResponse.next();
  }

  // If an Authorization header is present on an /app/* request, let it through.
  // Browser navigations without the header are handled by the client layout.
  if (pathname.startsWith("/app") && !hasAuthHeader) {
    // Don't hard-redirect here — the client layout will redirect once it
    // checks localStorage. A server redirect would break client-side JWT auth.
    return NextResponse.next();
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    // Run on all paths except Next.js internals and static assets
    "/((?!_next/static|_next/image|favicon\\.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico)$).*)",
  ],
};
