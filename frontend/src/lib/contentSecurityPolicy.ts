const NONCE_BYTES = 16;
const NONCE_PATTERN = /^[A-Za-z0-9+/_-]+={0,2}$/;
const ORIGIN_PATTERN = /^https:\/\/[a-z0-9.-]+(?::\d+)?$/;

export interface PolicyOptions {
  nonce: string;
  development: boolean;
  reportOrigin?: string | null;
}

export function createNonce(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(NONCE_BYTES));
  return btoa(String.fromCharCode(...bytes));
}

export function contentSecurityPolicy({ nonce, development, reportOrigin = null }: PolicyOptions): string {
  if (!NONCE_PATTERN.test(nonce)) throw new Error(`Nonce "${nonce}" is not base64`);
  if (reportOrigin !== null && !ORIGIN_PATTERN.test(reportOrigin)) throw new Error(`Report origin "${reportOrigin}" is not an https origin`);
  return [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'${development ? " 'unsafe-eval'" : ""}`,
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob:",
    "font-src 'self' data:",
    `connect-src 'self'${reportOrigin ? ` ${reportOrigin}` : ""}${development ? " ws: http://localhost:*" : ""}`,
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "object-src 'none'",
    ...(development ? [] : ["upgrade-insecure-requests"]),
  ].join("; ");
}
