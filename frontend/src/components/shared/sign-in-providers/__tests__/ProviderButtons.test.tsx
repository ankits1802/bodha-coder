import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ProviderButtons } from "../ProviderButtons";

describe("ProviderButtons", () => {
  it("shows nothing when no sign-in service is set up", () => {
    const { container } = render(<ProviderButtons providers={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("links each enabled service to its start route with its name", () => {
    render(<ProviderButtons providers={["google", "microsoft", "yahoo"]} />);
    expect(screen.getByRole("link", { name: "Continue with Google" })).toHaveAttribute("href", "/api/auth/google/start");
    expect(screen.getByRole("link", { name: "Continue with Microsoft" })).toHaveAttribute(
      "href",
      "/api/auth/microsoft/start",
    );
    expect(screen.getByRole("link", { name: "Continue with Yahoo" })).toHaveAttribute("href", "/api/auth/yahoo/start");
  });

  it("offers only the services it is given", () => {
    render(<ProviderButtons providers={["microsoft"]} />);
    expect(screen.getAllByRole("link")).toHaveLength(1);
    expect(screen.queryByRole("link", { name: "Continue with Google" })).not.toBeInTheDocument();
  });
});
