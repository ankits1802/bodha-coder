export interface RouteRedirect {
  source: string;
  destination: string;
  permanent: boolean;
}

export const ROUTE_REDIRECTS: readonly RouteRedirect[] = [
  { source: "/settings", destination: "/settings/setup", permanent: false },
  { source: "/setup", destination: "/settings/setup", permanent: true },
  { source: "/team", destination: "/settings/team", permanent: true },
  { source: "/plan", destination: "/settings/plan", permanent: true },
  { source: "/remittances", destination: "/billing/remittances", permanent: true },
  { source: "/quality", destination: "/insights/quality", permanent: true },
  { source: "/quality/review/:sampleId", destination: "/insights/quality/review/:sampleId", permanent: true },
];
