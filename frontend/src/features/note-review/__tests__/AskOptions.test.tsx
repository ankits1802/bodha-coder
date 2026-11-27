import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { AskOptions } from "../components/AskOptions";

function channelNames(): string[] {
  return screen.getAllByRole("radio").flatMap((radio) => (radio.tagName === "BUTTON" ? [radio.textContent ?? ""] : []));
}

describe("AskOptions", () => {
  it("offers email only while texts cannot be sent", () => {
    render(<AskOptions channel="email" onChannel={vi.fn()} canSendTexts={false} hold onHold={vi.fn()} />);
    expect(channelNames()).toEqual(["Email"]);
    expect(screen.getByRole("radio", { name: "Email" })).toBeChecked();
    expect(screen.queryByRole("radio", { name: "Text message" })).not.toBeInTheDocument();
  });

  it("offers a text message beside email when texts can be sent", () => {
    render(<AskOptions channel="sms" onChannel={vi.fn()} canSendTexts hold onHold={vi.fn()} />);
    expect(channelNames()).toEqual(["Text message", "Email"]);
    expect(screen.getByRole("radio", { name: "Text message" })).toBeChecked();
  });
});
