const NONCE_BYTES = 16;
const NONCE_PATTERN = /^[A-Za-z0-9+/_-]+={0,2}$/;

export interface PolicyOptions {
  nonce: string;
  development: boolean;
}

export function createNonce(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(NONCE_BYTES));
  return btoa(String.fromCharCode(...bytes));
}

export function contentSecurityPolicy({ nonce, development }: PolicyOptions): string {
  if (!NONCE_PATTERN.test(nonce)) throw new Error(`Nonce "${nonce}" is not base64`);
  return [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'${development ? " 'unsafe-eval'" : ""}`,
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob:",
    "font-src 'self' data:",
    `connect-src 'self'${development ? " ws: http://localhost:*" : ""}`,
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "object-src 'none'",
    ...(development ? [] : ["upgrade-insecure-requests"]),
  ].join("; ");
}
