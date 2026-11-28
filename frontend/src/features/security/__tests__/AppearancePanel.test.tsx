import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { getAppearance, saveAppearance } from "@/lib/api/account";
import { ApiError } from "@/lib/api/errors";
import type { Appearance } from "@/lib/api/types";
import { APPEARANCE_COOKIE, SYSTEM_APPEARANCE } from "@/lib/appearance";
import { clearSession, setSession } from "@/lib/session/store";
import { AppearancePanel } from "../AppearancePanel";

vi.mock("@/lib/api/account", () => ({ getAppearance: vi.fn(), saveAppearance: vi.fn() }));

const ATTRIBUTES = ["data-theme", "data-text-size", "data-motion"];

function choice(group: string, option: string): HTMLElement {
  return within(screen.getByRole("radiogroup", { name: group })).getByRole("radio", { name: option });
}

function echo(appearance: Appearance): Promise<Appearance> {
  return Promise.resolve(appearance);
}

describe("AppearancePanel", () => {
  beforeEach(() => {
    setSession({
      access_token: "token",
      user: { id: "user-1", name: "Priya Nair", email: "priya@example.com", role: "viewer", billing_only: false, practice: null, practices: [] },
    });
  });

  afterEach(() => {
    clearSession();
    vi.mocked(getAppearance).mockReset();
    vi.mocked(saveAppearance).mockReset();
    for (const name of ATTRIBUTES) document.documentElement.removeAttribute(name);
    document.cookie = `${APPEARANCE_COOKIE}=; Path=/; Max-Age=0`;
  });

  it("shows the person's saved theme, text size and motion", async () => {
    vi.mocked(getAppearance).mockResolvedValue({ theme: "light", text_size: "larger", reduce_motion: "off" });
    render(<AppearancePanel />);

    expect(await screen.findByRole("region", { name: "Appearance" })).toBeInTheDocument();
    await waitFor(() => expect(choice("Theme", "Light")).toHaveAttribute("aria-checked", "true"));
    expect(choice("Text size", "Larger")).toHaveAttribute("aria-checked", "true");
    expect(choice("Reduce motion", "Off")).toHaveAttribute("aria-checked", "true");
    expect(choice("Theme", "System")).toHaveAttribute("aria-checked", "false");
  });

  it("applies a choice at once and saves it for the person", async () => {
    vi.mocked(getAppearance).mockResolvedValue(SYSTEM_APPEARANCE);
    vi.mocked(saveAppearance).mockImplementation(echo);
    render(<AppearancePanel />);

    fireEvent.click(await screen.findByRole("radio", { name: "Dark" }));
    expect(document.documentElement).toHaveAttribute("data-theme", "dark");
    expect(document.cookie).toContain(`${APPEARANCE_COOKIE}=dark.default.system`);
    expect(choice("Theme", "Dark")).toHaveAttribute("aria-checked", "true");
    await waitFor(() => expect(saveAppearance).toHaveBeenCalledWith({ theme: "dark", text_size: "default", reduce_motion: "system" }));

    fireEvent.click(choice("Reduce motion", "On"));
    expect(document.documentElement).toHaveAttribute("data-motion", "reduce");
    await waitFor(() => expect(saveAppearance).toHaveBeenLastCalledWith({ theme: "dark", text_size: "default", reduce_motion: "on" }));
  });

  it("saves the latest of several quick choices once the earlier save returns", async () => {
    vi.mocked(getAppearance).mockResolvedValue(SYSTEM_APPEARANCE);
    let finishFirst: () => void = () => undefined;
    vi.mocked(saveAppearance)
      .mockImplementationOnce(
        (appearance) =>
          new Promise((resolve) => {
            finishFirst = () => resolve(appearance);
          }),
      )
      .mockImplementation(echo);
    render(<AppearancePanel />);

    fireEvent.click(await screen.findByRole("radio", { name: "Large" }));
    fireEvent.click(choice("Text size", "Larger"));
    fireEvent.click(choice("Text size", "Default"));
    fireEvent.click(choice("Text size", "Larger"));
    expect(document.documentElement).toHaveAttribute("data-text-size", "larger");
    expect(saveAppearance).toHaveBeenCalledTimes(1);

    finishFirst();
    await waitFor(() => expect(saveAppearance).toHaveBeenCalledTimes(2));
    expect(vi.mocked(saveAppearance).mock.calls.map(([sent]) => sent.text_size)).toEqual(["large", "larger"]);
  });

  it("keeps the choice on this device and says when it could not be saved", async () => {
    vi.mocked(getAppearance).mockResolvedValue(SYSTEM_APPEARANCE);
    vi.mocked(saveAppearance).mockRejectedValue(new ApiError(503, "unavailable", "The service is busy"));
    render(<AppearancePanel />);

    fireEvent.click(await screen.findByRole("radio", { name: "Larger" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("The service is busy");
    expect(document.documentElement).toHaveAttribute("data-text-size", "larger");
    expect(choice("Text size", "Larger")).toHaveAttribute("aria-checked", "true");
  });

  it("offers to try again when the saved appearance cannot be read", async () => {
    vi.mocked(getAppearance).mockRejectedValueOnce(new ApiError(503, "unavailable", "The service is busy")).mockResolvedValue(SYSTEM_APPEARANCE);
    render(<AppearancePanel />);

    fireEvent.click(await screen.findByRole("button", { name: "Try again" }));
    await waitFor(() => expect(choice("Theme", "System")).toHaveAttribute("aria-checked", "true"));
  });
});
