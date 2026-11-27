import { describe, expect, it, vi } from "vitest";
import { editRemote, forgetRemote, keepRemote, loadRemote, prefetchRemote, readRemote, writeRemote } from "../remoteCache";
import { rememberedParams } from "../useRememberedParams";

describe("remote cache", () => {
  it("serves an entry until it expires", () => {
    keepRemote("places", ["11"], 60, 1_000);
    expect(readRemote("places", 60_999)).toEqual(["11"]);
    expect(readRemote("places", 61_000)).toBeUndefined();
    expect(readRemote("places", 1_000)).toBeUndefined();
  });

  it("changes only entries it holds", () => {
    writeRemote("missing", 1);
    expect(readRemote("missing")).toBeUndefined();
    keepRemote("order", [1, 2, 3], 60);
    editRemote<number[]>("order", (items) => items.filter((item) => item !== 2));
    expect(readRemote("order")).toEqual([1, 3]);
    writeRemote("order", [9]);
    expect(readRemote("order")).toEqual([9]);
    forgetRemote("order");
    expect(readRemote("order")).toBeUndefined();
  });

  it("loads a prefetched note once and shares the request still running", async () => {
    const load = vi.fn(() => Promise.resolve({ id: "note-1" }));
    prefetchRemote("note:note-1", load);
    prefetchRemote("note:note-1", load);
    await expect(loadRemote("note:note-1", load, 0)).resolves.toEqual({ id: "note-1" });
    expect(load).toHaveBeenCalledTimes(1);
    expect(readRemote("note:note-1")).toEqual({ id: "note-1" });
  });

  it("starts a fresh request when asked not to join", async () => {
    const load = vi.fn(() => Promise.resolve(1));
    const first = loadRemote("today", load, 0);
    const second = loadRemote("today", load, 0, false);
    await Promise.all([first, second]);
    expect(load).toHaveBeenCalledTimes(2);
    expect(readRemote("today")).toBeUndefined();
  });
});

describe("remembered filters", () => {
  it("keeps only the named filters, never the search text", () => {
    const search = new URLSearchParams("lane=coder&search=reyes&assigned=me&offset=50");
    expect(rememberedParams(search, ["lane", "assigned", "provider_id"])).toBe("lane=coder&assigned=me");
    expect(rememberedParams(new URLSearchParams(""), ["lane"])).toBe("");
  });
});
