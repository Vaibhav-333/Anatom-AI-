import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const PUBLIC_PATHS = ["/login", "/signup", "/forgot-password"];
const HEALTH_PROFILE_PATH = "/health-profile";

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // DEV BYPASS — anatom_auth cookie set by devSkip() is enough to pass through
  const isAuth = request.cookies.has("anatom_auth");

  const isPublic = PUBLIC_PATHS.some((p) => pathname.startsWith(p));
  const isHealthProfile = pathname.startsWith(HEALTH_PROFILE_PATH);

  // Unauthenticated → send to login
  if (!isAuth && !isPublic && !isHealthProfile) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    return NextResponse.redirect(url);
  }

  // Authenticated on public auth pages → send to dashboard
  if (isAuth && isPublic) {
    const url = request.nextUrl.clone();
    url.pathname = "/";
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    // Skip Next.js internals, static files, and API routes
    "/((?!_next/static|_next/image|favicon.ico|api/).*)",
  ],
};
