import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { getCharges, setCharge } from "@/lib/api/clearinghouse";
import { centsFrom, validateCharge } from "../chargeForm";
import { ChargesPanel } from "../ChargesPanel";

vi.mock("@/lib/api/clearinghouse", () => ({ getCharges: vi.fn(), setCharge: vi.fn(), removeCharge: vi.fn(), importCharges: vi.fn() }));

describe("charge amounts", () => {
  it("turns dollars into cents and refuses what is not an amount", () => {
    expect(centsFrom("150")).toBe(15000);
    expect(centsFrom("$150.5")).toBe(15050);
    expect(centsFrom("1,250.05")).toBe(125005);
    expect(centsFrom("12.345")).toBeNull();
    expect(centsFrom("0")).toBeNull();
    expect(centsFrom("abc")).toBeNull();
  });

  it("needs a CPT or HCPCS code", () => {
    expect(validateCharge({ code: "99214", amount: "150" })).toEqual({});
    expect(validateCharge({ code: "g2211", amount: "16.05" })).toEqual({});
    expect(validateCharge({ code: "E11.9", amount: "150" }).code).toBe("Use a CPT or HCPCS code, like 99214 or G2211");
  });
});

describe("ChargesPanel", () => {
  afterEach(() => {
    vi.mocked(setCharge).mockReset();
  });

  it("lists the charges as money and saves a new charge in cents", async () => {
    vi.mocked(getCharges).mockResolvedValue({ items: [{ code: "99213", cents: 9500 }] });
    vi.mocked(setCharge).mockResolvedValue({ items: [{ code: "99213", cents: 9500 }, { code: "99214", cents: 125050 }] });
    render(<ChargesPanel />);
    expect(await screen.findByText("$95.00")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Add charge" }));
    fireEvent.change(screen.getByLabelText("CPT or HCPCS code"), { target: { value: "99214" } });
    fireEvent.change(screen.getByLabelText("Charge"), { target: { value: "$1,250.50" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(setCharge).toHaveBeenCalledWith("99214", 125050));
    expect(await screen.findByText("$1,250.50")).toBeInTheDocument();
  });
});
