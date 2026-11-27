import { NextResponse, type NextRequest, type ProxyConfig } from "next/server";
import { contentSecurityPolicy, createNonce } from "@/lib/contentSecurityPolicy";
import { adminUrl, siteUrl } from "@/lib/site";

const POLICY_HEADER = "Content-Security-Policy";
const HQ_HOME = "/hq";
const SHARED_PAGES: readonly string[] = ["/sign-in", "/forgot-password", "/set-password"];

function isHqPage(pathname: string): boolean {
  return pathname === HQ_HOME || pathname.startsWith(`${HQ_HOME}/`);
}

function requestHost(request: NextRequest): string {
  return (request.headers.get("host") ?? request.nextUrl.host).toLowerCase();
}

function otherHost(request: NextRequest): URL | null {
  const admin = adminUrl();
  const main = siteUrl();
  if (!admin || new URL(admin).host === new URL(main).host) return null;
  const { pathname, search } = request.nextUrl;
  if (requestHost(request) !== new URL(admin).host) {
    return isHqPage(pathname) ? new URL(`${pathname}${search}`, admin) : null;
  }
  if (pathname === "/") return new URL(HQ_HOME, admin);
  if (isHqPage(pathname) || SHARED_PAGES.includes(pathname)) return null;
  return new URL(`${pathname}${search}`, main);
}

export function proxy(request: NextRequest): NextResponse {
  const destination = otherHost(request);
  if (destination) return NextResponse.redirect(destination);
  const policy = contentSecurityPolicy({ nonce: createNonce(), development: process.env.NODE_ENV === "development" });
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set(POLICY_HEADER, policy);
  const response = NextResponse.next({ request: { headers: requestHeaders } });
  response.headers.set(POLICY_HEADER, policy);
  return response;
}

export const config: ProxyConfig = {
  matcher: [
    {
      source:
        "/((?!api(?:/|$)|_next/static|_next/image|icon\\.svg$|opengraph-image$|robots\\.txt$|sitemap\\.xml$|manifest\\.webmanifest$).*)",
      missing: [
        { type: "header", key: "next-router-prefetch" },
        { type: "header", key: "purpose", value: "prefetch" },
      ],
    },
  ],
};
