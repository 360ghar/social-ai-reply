import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const PROTECTED_PREFIX = "/app";
const AUTH_PAGES = ["/login", "/register", "/reset-password", "/auth/setup"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  // Check for server-validated session cookie (set by auth-provider after successful auth)
  const hasSession = request.cookies.get("rf_has_session")?.value === "1";

  // Redirect unauthenticated users away from protected routes
  if (pathname.startsWith(PROTECTED_PREFIX) && !hasSession) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    return NextResponse.redirect(url);
  }

  // Redirect authenticated users away from login/register pages
  if (AUTH_PAGES.some((p) => pathname === p || pathname.startsWith(p + "/")) && hasSession) {
    const url = request.nextUrl.clone();
    url.pathname = "/app/dashboard";
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/app/:path*", "/app", "/login", "/register", "/reset-password", "/auth/setup"],
};
