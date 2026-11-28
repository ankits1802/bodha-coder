import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CODER } from "@/features/queue/__tests__/fixtures";
import { clearSession, setSession } from "@/lib/session/store";
import { OrganizationArea } from "../OrganizationArea";
import { ORGANIZATION_ADMIN, ORGANIZATION_ID } from "./organizationFixtures";

const navigation = vi.hoisted(() => ({ pathname: "/organizations/org-1", push: vi.fn() }));
vi.mock("next/navigation", () => ({
  usePathname: () => navigation.pathname,
  useRouter: () => ({ push: navigation.push, replace: vi.fn() }),
}));

describe("OrganizationArea", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    navigation.pathname = "/organizations/org-1";
  });

  afterEach(() => clearSession());

  it("shows the organization's tabs and moves between them", async () => {
    setSession({ access_token: "token", user: ORGANIZATION_ADMIN });
    navigation.pathname = "/organizations/org-1/insights";
    const events = userEvent.setup();
    render(
      <OrganizationArea organizationId={ORGANIZATION_ID}>
        <p>Inside</p>
      </OrganizationArea>,
    );
    expect(screen.getByRole("tablist", { name: "Acme Health" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Insights" })).toHaveAttribute("aria-selected", "true");
    await events.click(screen.getByRole("tab", { name: "Domains" }));
    expect(navigation.push).toHaveBeenCalledWith("/organizations/org-1/domains");
    await events.click(screen.getByRole("tab", { name: "Single sign-on" }));
    expect(navigation.push).toHaveBeenCalledWith("/organizations/org-1/sign-in");
    await events.click(screen.getByRole("tab", { name: "Practices" }));
    expect(navigation.push).toHaveBeenCalledWith("/organizations/org-1");
  });

  it("refuses someone who does not run the organization", () => {
    setSession({ access_token: "token", user: CODER });
    render(
      <OrganizationArea organizationId={ORGANIZATION_ID}>
        <p>Inside</p>
      </OrganizationArea>,
    );
    expect(screen.getByText("You can't open this organization")).toBeInTheDocument();
    expect(screen.queryByText("Inside")).not.toBeInTheDocument();
  });

  it("shows only the page without tabs in a billing-only session", () => {
    setSession({ access_token: "token", user: { ...ORGANIZATION_ADMIN, billing_only: true } });
    navigation.pathname = "/organizations/org-1/plan";
    render(
      <OrganizationArea organizationId={ORGANIZATION_ID}>
        <p>Inside</p>
      </OrganizationArea>,
    );
    expect(screen.getByText("Inside")).toBeInTheDocument();
    expect(screen.queryByRole("tablist")).not.toBeInTheDocument();
  });
});
