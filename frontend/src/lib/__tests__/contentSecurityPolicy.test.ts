import { describe, expect, it } from "vitest";
import { contentSecurityPolicy, createNonce } from "@/lib/contentSecurityPolicy";

const NONCE = "q1w2e3r4t5y6u7i8o9p0Aa==";

function directive(policy: string, name: string): string | undefined {
  return policy.split("; ").find((entry) => entry.startsWith(`${name} `));
}

describe("contentSecurityPolicy", () => {
  it("lets only the request's nonce start scripts in production", () => {
    expect(contentSecurityPolicy({ nonce: NONCE, development: false })).toBe(
      "default-src 'self'; " +
        "script-src 'self' 'nonce-q1w2e3r4t5y6u7i8o9p0Aa==' 'strict-dynamic'; " +
        "style-src 'self' 'unsafe-inline'; " +
        "img-src 'self' data: blob:; " +
        "font-src 'self' data:; " +
        "connect-src 'self'; " +
        "frame-ancestors 'none'; " +
        "base-uri 'self'; " +
        "form-action 'self'; " +
        "object-src 'none'; " +
        "upgrade-insecure-requests",
    );
  });

  it("adds eval and the dev server's connections in development and keeps plain http", () => {
    expect(contentSecurityPolicy({ nonce: NONCE, development: true })).toBe(
      "default-src 'self'; " +
        "script-src 'self' 'nonce-q1w2e3r4t5y6u7i8o9p0Aa==' 'strict-dynamic' 'unsafe-eval'; " +
        "style-src 'self' 'unsafe-inline'; " +
        "img-src 'self' data: blob:; " +
        "font-src 'self' data:; " +
        "connect-src 'self' ws: http://localhost:*; " +
        "frame-ancestors 'none'; " +
        "base-uri 'self'; " +
        "form-action 'self'; " +
        "object-src 'none'",
    );
  });

  it.each([false, true])("never allows inline scripts (development %s)", (development) => {
    const scripts = directive(contentSecurityPolicy({ nonce: NONCE, development }), "script-src");
    expect(scripts).toBeDefined();
    expect(scripts).not.toContain("'unsafe-inline'");
  });

  it.each(["", "abc' 'unsafe-inline", "abc; script-src *", "a b"])("refuses the nonce %j", (nonce) => {
    expect(() => contentSecurityPolicy({ nonce, development: false })).toThrow("is not base64");
  });
});

describe("createNonce", () => {
  it("encodes sixteen random bytes as base64", () => {
    expect(createNonce()).toMatch(/^[A-Za-z0-9+/]{22}==$/);
  });

  it("is different on every call", () => {
    const nonces = new Set(Array.from({ length: 64 }, () => createNonce()));
    expect(nonces.size).toBe(64);
  });

  it("is accepted by the policy", () => {
    const nonce = createNonce();
    expect(directive(contentSecurityPolicy({ nonce, development: false }), "script-src")).toBe(
      `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'`,
    );
  });
});
