export function siteUrl(): string {
  if (process.env.SITE_URL) return process.env.SITE_URL;
  return "http://localhost:3000";
}

export function adminUrl(): string | null {
  const address = process.env.ADMIN_URL?.trim().replace(/\/+$/, "");
  return address ? address : null;
}
