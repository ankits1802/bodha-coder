import { connection } from "next/server";
import { describe, expect, it, vi } from "vitest";
import RootLayout from "@/app/layout";

vi.mock("next/font/google", () => ({ Inter: () => ({ variable: "font-inter" }) }));
vi.mock("next/server", () => ({ connection: vi.fn(async () => undefined) }));

describe("RootLayout", () => {
  it("renders at request time, so every page carries that request's nonce", async () => {
    await RootLayout({ children: null });
    expect(connection).toHaveBeenCalledTimes(1);
  });
});
