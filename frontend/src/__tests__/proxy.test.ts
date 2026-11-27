import { unstable_doesMiddlewareMatch, unstable_getResponseFromNextConfig } from "next/experimental/testing/server";
import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { config, proxy } from "@/proxy";
import nextConfig from "../../next.config";

const SITE = "https://bodha.test";
const NONCE_SOURCE = /'nonce-([A-Za-z0-9+/]{22}==)'/;

function runsOn(path: string, headers: Record<string, string> = {}): boolean {
  return unstable_doesMiddlewareMatch({ config, url: `${SITE}${path}`, headers });
}

function policyFor(path: string): string | null {
  return proxy(new NextRequest(`${SITE}${path}`)).headers.get("content-security-policy");
}

describe("proxy", () => {
  it("sends the strict policy with the request's nonce outside development", () => {
    const policy = policyFor("/today");
    expect(policy).toMatch(NONCE_SOURCE);
    expect(policy).not.toContain("'unsafe-eval'");
    expect(policy).toContain("upgrade-insecure-requests");
  });

  it("hands the same policy to the renderer, which reads the nonce from the request", () => {
    const response = proxy(new NextRequest(`${SITE}/pricing`));
    expect(response.headers.get("x-middleware-next")).toBe("1");
    expect(response.headers.get("x-middleware-request-content-security-policy")).toBe(
      response.headers.get("content-security-policy"),
    );
  });

  it("makes a new nonce for every request", () => {
    const nonces = ["/", "/", "/queue"].map((path) => policyFor(path)?.match(NONCE_SOURCE)?.[1]);
    expect(nonces.every(Boolean)).toBe(true);
    expect(new Set(nonces).size).toBe(3);
  });
});

const ADMIN = "https://admin.bodha.test";
const SERVER = "http://0.0.0.0:3000";

function visit(host: string, path: string) {
  return proxy(new NextRequest(`${SERVER}${path}`, { headers: { host } }));
}

function servedHere(response: ReturnType<typeof proxy>): boolean {
  return response.headers.get("x-middleware-next") === "1" && response.headers.get("content-security-policy") !== null;
}

describe("proxy host routing", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  describe("with ADMIN_URL unset", () => {
    beforeEach(() => {
      vi.stubEnv("SITE_URL", SITE);
      vi.stubEnv("ADMIN_URL", "");
    });

    it.each(["/", "/hq", "/hq/practices", "/hq/team", "/today", "/sign-in"])("serves %s on the one host", (path) => {
      expect(servedHere(visit("bodha.test", path))).toBe(true);
    });
  });

  describe("with ADMIN_URL set", () => {
    beforeEach(() => {
      vi.stubEnv("SITE_URL", SITE);
      vi.stubEnv("ADMIN_URL", `${ADMIN}/`);
    });

    it("sends the admin host's front page to the HQ home", () => {
      const response = visit("admin.bodha.test", "/");
      expect(response.status).toBe(307);
      expect(response.headers.get("location")).toBe(`${ADMIN}/hq`);
    });

    it.each(["/hq", "/hq/practices", "/hq/team", "/hq/security", "/sign-in", "/forgot-password", "/set-password"])(
      "serves %s on the admin host",
      (path) => {
        expect(servedHere(visit("admin.bodha.test", path))).toBe(true);
      },
    );

    it.each(["/today", "/queue?lane=coder", "/pricing", "/sign-up/practice", "/respond", "/legal/terms", "/hqx"])(
      "sends the practice page %s from the admin host to the main host",
      (path) => {
        const response = visit("Admin.Bodha.test", path);
        expect(response.status).toBe(307);
        expect(response.headers.get("location")).toBe(`${SITE}${path}`);
      },
    );

    it.each(["/hq", "/hq/practices?status=trial", "/hq/team"])("sends %s from the main host to the admin host", (path) => {
      const response = visit("bodha.test", path);
      expect(response.status).toBe(307);
      expect(response.headers.get("location")).toBe(`${ADMIN}${path}`);
    });

    it.each(["/", "/today", "/sign-in", "/pricing", "/respond"])("serves %s on the main host", (path) => {
      expect(servedHere(visit("bodha.test", path))).toBe(true);
    });

    it("routes nothing when ADMIN_URL names the main host", () => {
      vi.stubEnv("ADMIN_URL", SITE);
      expect(servedHere(visit("bodha.test", "/hq/practices"))).toBe(true);
    });
  });
});

describe("proxy matcher", () => {
  it.each([
    "/",
    "/pricing",
    "/legal/terms",
    "/sign-in",
    "/sign-up/practice",
    "/today",
    "/notes/0f9c2a",
    "/quality/review/12",
    "/hq/practices",
    "/respond",
  ])("runs on the page %s", (path) => {
    expect(runsOn(path)).toBe(true);
  });

  it("runs on a missing file, whose not-found page is HTML", () => {
    expect(runsOn("/favicon.ico")).toBe(true);
  });

  it.each([
    "/api",
    "/api/notes",
    "/api/uploads/batch",
    "/_next/static/chunks/main-app.js",
    "/_next/static/media/inter.woff2",
    "/_next/image?url=%2Ficon.svg&w=64&q=75",
    "/icon.svg",
    "/opengraph-image",
    "/robots.txt",
    "/sitemap.xml",
    "/manifest.webmanifest",
  ])("skips %s", (path) => {
    expect(runsOn(path)).toBe(false);
  });

  it("skips router prefetches", () => {
    expect(runsOn("/queue", { "next-router-prefetch": "1" })).toBe(false);
    expect(runsOn("/queue", { purpose: "prefetch" })).toBe(false);
  });
});

describe("next.config headers", () => {
  it.each(["/", "/_next/static/chunks/main-app.js", "/robots.txt"])(
    "keeps the other security headers on %s and leaves the policy to the proxy",
    async (path) => {
      const response = await unstable_getResponseFromNextConfig({ url: `${SITE}${path}`, nextConfig });
      expect(response.headers.get("content-security-policy")).toBeNull();
      expect(response.headers.get("x-frame-options")).toBe("DENY");
      expect(response.headers.get("x-content-type-options")).toBe("nosniff");
      expect(response.headers.get("referrer-policy")).toBe("no-referrer");
      expect(response.headers.get("permissions-policy")).toBe("camera=(), microphone=(), geolocation=()");
    },
  );
});
