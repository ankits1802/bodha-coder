import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { forgetRemote } from "@/hooks/remoteCache";
import { getIntake } from "@/lib/api/intake";
import type { IntakeView } from "@/lib/api/types";
import { IntakeSettings } from "../IntakeSettings";

vi.mock("@/lib/api/intake", () => ({ getIntake: vi.fn(), saveIntake: vi.fn() }));
vi.mock("@/lib/api/uploads", () => ({ getProviders: vi.fn().mockResolvedValue([]), getPlaces: vi.fn().mockResolvedValue([]) }));

const ON: IntakeView = { enabled: true, prefix: "inbox", provider_by_folder: {}, place_code: "11", visit_type: "Established patient" };

describe("IntakeSettings", () => {
  it("tells the admin whether dropped PDFs are read, without any storage path", async () => {
    forgetRemote("practice-intake");
    vi.mocked(getIntake).mockResolvedValue(ON);
    const { container } = render(<IntakeSettings />);
    expect(await screen.findByText("Reading dropped PDFs")).toBeInTheDocument();
    expect(container).not.toHaveTextContent("practices/");
  });

  it("says Off while intake is off", async () => {
    forgetRemote("practice-intake");
    vi.mocked(getIntake).mockResolvedValue({ ...ON, enabled: false });
    render(<IntakeSettings />);
    expect(await screen.findByText("Off")).toBeInTheDocument();
  });
});
