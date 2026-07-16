import { NextRequest, NextResponse } from "next/server";

const SESSION_COOKIE = "lenquant_session";

export function middleware(request: NextRequest) {
  const host = request.headers.get("host") ?? "";

  // Public preview subdomain — always pass through, no auth check
  if (host.startsWith("sites.")) {
    return NextResponse.next();
  }

  const { pathname } = request.nextUrl;
  const hasSessionCookie = !!request.cookies.get(SESSION_COOKIE)?.value;

  // Also check for JWT in localStorage (handled client-side) or Authorization header
  const hasAuthHeader = !!request.headers.get("authorization");
  const isAuthenticated = hasSessionCookie || hasAuthHeader;

  // Allow access to auth pages without authentication
  if (pathname === "/login" || pathname === "/signup" || pathname === "/verify-email") {
    // If already authenticated, redirect to dashboard from login/signup
    if (isAuthenticated && (pathname === "/login" || pathname === "/signup")) {
      return NextResponse.redirect(new URL("/app", request.url));
    }
    return NextResponse.next();
  }

  // Unauthenticated user on /app/* → redirect to login
  if (pathname.startsWith("/app") && !isAuthenticated) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    // Run on all paths except Next.js internals and static assets
    "/((?!_next/static|_next/image|favicon\\.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico)$).*)",
  ],
};
