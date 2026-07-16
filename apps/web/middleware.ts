import { NextRequest, NextResponse } from "next/server";

const SESSION_COOKIE_NAME = "lenquant_session";

const protectedRoutes = ["/nsa"];
const publicRoutes = ["/", "/landing", "/login", "/sites", "/api"];

export function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;

  // Allow public routes
  const isPublic = publicRoutes.some((route) => pathname === route || pathname.startsWith(`${route}/`));
  if (isPublic) {
    return NextResponse.next();
  }

  // Check protected routes
  const isProtected = protectedRoutes.some((route) => pathname === route || pathname.startsWith(`${route}/`));
  if (!isProtected) {
    return NextResponse.next();
  }

  const session = request.cookies.get(SESSION_COOKIE_NAME);
  if (!session) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", `${pathname}${search}`);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next|static|favicon.ico|.*\\..*).*)"]
};

