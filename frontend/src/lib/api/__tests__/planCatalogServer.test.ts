import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CATALOG } from "@/components/shared/plan-cards/__tests__/planFixtures";
import { loadPlanCatalog } from "../planCatalogServer";

const fetchMock = vi.fn<typeof fetch>();

describe("loadPlanCatalog", () => {
  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
    vi.stubEnv("BACKEND_URL", "http://api.internal:8000");
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it("reads the catalog from the backend and keeps it for an hour", async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify(CATALOG), { status: 200, headers: { "Content-Type": "application/json" } }));
    expect(await loadPlanCatalog()).toEqual(CATALOG);
    expect(fetchMock).toHaveBeenCalledWith("http://api.internal:8000/api/plans", expect.objectContaining({ next: { revalidate: 3600 } }));
  });

  it("has no catalog when the backend cannot be reached", async () => {
    fetchMock.mockRejectedValue(new TypeError("fetch failed"));
    expect(await loadPlanCatalog()).toBeNull();
  });

  it("has no catalog when the backend answers with an error", async () => {
    fetchMock.mockResolvedValue(new Response("unavailable", { status: 503 }));
    expect(await loadPlanCatalog()).toBeNull();
  });
});
