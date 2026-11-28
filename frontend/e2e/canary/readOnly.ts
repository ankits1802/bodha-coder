import type { Page } from "@playwright/test";

const SIGN_IN_WRITES = new Set(["/api/auth/login", "/api/auth/mfa/verify", "/api/auth/refresh"]);
const READS = new Set(["GET", "HEAD"]);
const REFRESH = "/api/auth/refresh";
const UNAUTHORIZED = 401;
const FIRST_ERROR_STATUS = 400;

export interface Problems {
  refused: string[];
  failed: string[];
}

export function setting(name: string): string {
  const value = process.env[name];
  if (!value) throw new Error(`set ${name}`);
  return value;
}

export async function keepReadOnly(page: Page): Promise<Problems> {
  const problems: Problems = { refused: [], failed: [] };
  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const { pathname } = new URL(request.url());
    if (READS.has(request.method()) || (request.method() === "POST" && SIGN_IN_WRITES.has(pathname))) {
      await route.continue();
      return;
    }
    problems.refused.push(`${request.method()} ${pathname}`);
    await route.abort("blockedbyclient");
  });
  page.on("response", (response) => {
    const { pathname } = new URL(response.url());
    const expected = pathname === REFRESH && response.status() === UNAUTHORIZED;
    if (pathname.startsWith("/api/") && response.status() >= FIRST_ERROR_STATUS && !expected) {
      problems.failed.push(`${response.request().method()} ${pathname} answered ${response.status()}`);
    }
  });
  return problems;
}
