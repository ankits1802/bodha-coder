import type { ErrorEvent } from "@sentry/nextjs";
import { describe, expect, it } from "vitest";
import { REDACTED, routeOf, scrubBreadcrumb, scrubEvent } from "../scrub";

const PATIENT = "REYES MARISOL 1959-03-02";

describe("scrubEvent", () => {
  it("keeps the exception type and frames and drops messages, values, people, requests and breadcrumb text", () => {
    const event: ErrorEvent = {
      type: undefined,
      event_id: "e1",
      level: "error",
      release: "4f2a9c1",
      environment: "production",
      message: `could not open ${PATIENT}`,
      transaction: "/notes/3f1c2a9e-5b7d-4c11-9e2a-000000000001",
      exception: {
        values: [
          {
            type: "TypeError",
            value: `Cannot read ${PATIENT}`,
            mechanism: { type: "onerror", handled: false, data: { note: PATIENT } },
            stacktrace: {
              frames: [
                {
                  filename: "https://www.bodhaai.co/_next/static/chunks/app/page-3a9f.js?q=REYES",
                  function: "render",
                  lineno: 12,
                  colno: 4,
                  in_app: true,
                  vars: { patient: PATIENT },
                  context_line: PATIENT,
                },
              ],
            },
          },
        ],
      },
      request: { url: `https://www.bodhaai.co/queue?q=${PATIENT}#token`, headers: { Cookie: "s=1" } },
      user: { email: "coder@lakeside.example.com", ip_address: "203.0.113.9" },
      extra: { patient: PATIENT },
      contexts: { browser: { name: "Safari" } },
      breadcrumbs: [{ category: "ui.click", message: PATIENT, data: { text: PATIENT }, level: "info", timestamp: 1 }],
    };

    expect(scrubEvent(event)).toEqual({
      type: undefined,
      event_id: "e1",
      level: "error",
      release: "4f2a9c1",
      environment: "production",
      message: REDACTED,
      transaction: "/notes/:id",
      exception: {
        values: [
          {
            type: "TypeError",
            value: REDACTED,
            mechanism: { type: "onerror", handled: false },
            stacktrace: {
              frames: [
                {
                  filename: "https://www.bodhaai.co/_next/static/chunks/app/page-3a9f.js",
                  function: "render",
                  lineno: 12,
                  colno: 4,
                  in_app: true,
                },
              ],
            },
          },
        ],
      },
      request: { url: "/queue" },
      breadcrumbs: [{ category: "ui.click", level: "info", timestamp: 1 }],
    });
  });

  it("keeps a browser network message that names no data", () => {
    const event: ErrorEvent = { type: undefined, exception: { values: [{ type: "TypeError", value: "Failed to fetch" }] } };
    expect(scrubEvent(event).exception?.values?.[0]?.value).toBe("Failed to fetch");
  });
});

describe("routeOf", () => {
  it("masks every path segment that holds a digit and drops the query and fragment", () => {
    expect(routeOf("https://www.bodhaai.co/verify/AB12CD?x=1#t")).toBe("/verify/:id");
    expect(routeOf("/settings/setup")).toBe("/settings/setup");
  });
});

describe("scrubBreadcrumb", () => {
  it("keeps where and when, never what", () => {
    expect(scrubBreadcrumb({ type: "http", category: "fetch", data: { url: PATIENT }, message: PATIENT })).toEqual({
      type: "http",
      category: "fetch",
    });
  });
});
