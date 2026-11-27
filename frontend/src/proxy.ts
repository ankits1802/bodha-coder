import { NextResponse, type NextRequest, type ProxyConfig } from "next/server";
import { contentSecurityPolicy, createNonce } from "@/lib/contentSecurityPolicy";

const POLICY_HEADER = "Content-Security-Policy";

export function proxy(request: NextRequest): NextResponse {
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
