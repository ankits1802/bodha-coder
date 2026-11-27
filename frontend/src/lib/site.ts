export function siteUrl(): string {
  if (process.env.SITE_URL) return process.env.SITE_URL;
  if (process.env.VERCEL_PROJECT_PRODUCTION_URL) return `https://${process.env.VERCEL_PROJECT_PRODUCTION_URL}`;
  return "http://localhost:3000";
}

export function adminUrl(): string | null {
  const address = process.env.ADMIN_URL?.trim().replace(/\/+$/, "");
  return address ? address : null;
}
