import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const API_BASE_URL =
  process.env.INTERNAL_API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const PUBLIC_PATHS = ["/login", "/register"];
const ONBOARDING_PREFIX = "/onboarding";

type AuthUser = {
  onboarding_complete: boolean;
};

async function fetchCurrentUser(token: string): Promise<AuthUser | null> {
  try {
    const response = await fetch(`${API_BASE_URL}/users/me`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    if (!response.ok) {
      return null;
    }
    return (await response.json()) as AuthUser;
  } catch {
    return null;
  }
}

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const token = request.cookies.get("streamwise_token")?.value;

  const isPublicPath = PUBLIC_PATHS.some(
    (path) => pathname === path || pathname.startsWith(`${path}/`),
  );
  const isOnboardingPath =
    pathname === ONBOARDING_PREFIX || pathname.startsWith(`${ONBOARDING_PREFIX}/`);

  if (!token) {
    if (isPublicPath) {
      return NextResponse.next();
    }
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }

  const user = await fetchCurrentUser(token);

  if (user === null) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", pathname);
    const response = NextResponse.redirect(loginUrl);
    response.cookies.delete("streamwise_token");
    return response;
  }

  if (isPublicPath) {
    return NextResponse.redirect(new URL("/", request.url));
  }

  if (!user.onboarding_complete && !isOnboardingPath) {
    return NextResponse.redirect(new URL(ONBOARDING_PREFIX, request.url));
  }

  if (user.onboarding_complete && isOnboardingPath) {
    return NextResponse.redirect(new URL("/", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
