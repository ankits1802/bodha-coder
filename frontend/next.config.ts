import type { NextConfig } from "next";
import { backendUrl } from "./src/lib/backend";
import { ROUTE_REDIRECTS } from "./src/lib/routeRedirects";

const securityHeaders = [
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "no-referrer" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
];

const nextConfig: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  agentRules: false,
  async redirects() {
    return ROUTE_REDIRECTS.map((route) => ({ ...route }));
  },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${backendUrl()}/api/:path*` }];
  },
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
};

export default nextConfig;
