import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useAction } from "@/hooks/useAction";
import { ApiError } from "@/lib/api/errors";
import { adoptSignature, draftSignature } from "@/lib/api/signatures";
import type { SignatureView } from "@/lib/api/types";
import { clearSession, setSession } from "@/lib/session/store";
import { SignatureGateDialog } from "../SignatureDialog";
import { draftFrom } from "../signatureImage";
import { useSignatureGate } from "../useSignatureGate";

vi.mock("@/lib/api/signatures", () => ({ draftSignature: vi.fn(), adoptSignature: vi.fn() }));
vi.mock("../signatureImage", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../signatureImage")>()),
  draftFrom: vi.fn(),
}));

const DRAFT: SignatureView = {
  id: "signature-1",
  source: "typed",
  typed_name: "Cora Coder",
  image: "data:image/png;base64,iVBORw0KGgo=",
  created_at: "2026-11-28T10:00:00+00:00",
};
const BODY = { source: "typed" as const, typed_name: "Cora Coder", image: DRAFT.image };
const NEEDS_SIGNATURE = new ApiError(409, "signature_required", "add your signature before approving");

function Approve({ approve }: { approve: () => Promise<{ status: string }> }) {
  const gate = useSignatureGate();
  const action = useAction(gate.gated(approve));
  return (
    <>
      <button type="button" onClick={() => void action.run()}>
        Approve
      </button>
      {action.pending ? <span>Approving</span> : null}
      {action.error ? <p>{action.error}</p> : null}
      <SignatureGateDialog gate={gate} />
    </>
  );
}

beforeEach(() => {
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
  setSession({
    access_token: "token",
    user: { id: "user-1", name: "Cora Coder", email: "cora@example.com", role: "coder", billing_only: false, practice: null },
  });
});

afterEach(() => clearSession());

describe("signing on the first approval", () => {
  it("asks for a signature once, then approves without another click", async () => {
    const user = userEvent.setup();
    const approve = vi.fn().mockRejectedValueOnce(NEEDS_SIGNATURE).mockResolvedValueOnce({ status: "approved" });
    vi.mocked(draftFrom).mockResolvedValue(BODY);
    vi.mocked(draftSignature).mockResolvedValue(DRAFT);
    vi.mocked(adoptSignature).mockResolvedValue({ signature: DRAFT });
    render(<Approve approve={approve} />);

    await user.click(screen.getByRole("button", { name: "Approve" }));
    expect(await screen.findByRole("heading", { name: "Add your signature" })).toBeInTheDocument();
    expect(screen.getByText("Approving")).toBeInTheDocument();

    screen.getByRole("radio", { name: "Draw" }).focus();
    await user.keyboard("{ArrowRight}");
    expect(screen.getByRole("textbox", { name: "Full name" })).toHaveValue("Cora Coder");
    await user.click(screen.getByRole("button", { name: "Continue" }));
    await user.click(await screen.findByRole("button", { name: "Adopt signature" }));

    await waitFor(() => expect(approve).toHaveBeenCalledTimes(2));
    expect(draftFrom).toHaveBeenCalledWith(expect.objectContaining({ mode: "typed", name: "Cora Coder" }));
    expect(draftSignature).toHaveBeenCalledWith(BODY);
    expect(adoptSignature).toHaveBeenCalledWith("signature-1");
    await waitFor(() => expect(screen.queryByText("Approving")).not.toBeInTheDocument());
    expect(screen.queryByRole("heading", { name: "Add your signature" })).not.toBeInTheDocument();
    expect(screen.queryByText(/signature/i)).not.toBeInTheDocument();
  });

  it("approves at once when a signature is already adopted", async () => {
    const user = userEvent.setup();
    const approve = vi.fn().mockResolvedValue({ status: "approved" });
    render(<Approve approve={approve} />);

    await user.click(screen.getByRole("button", { name: "Approve" }));

    await waitFor(() => expect(approve).toHaveBeenCalledTimes(1));
    expect(screen.queryByRole("heading", { name: "Add your signature" })).not.toBeInTheDocument();
    expect(draftSignature).not.toHaveBeenCalled();
  });

  it("passes any other refusal through unchanged", async () => {
    const user = userEvent.setup();
    const approve = vi.fn().mockRejectedValue(new ApiError(409, "conflict", "there are no codes to bill"));
    render(<Approve approve={approve} />);

    await user.click(screen.getByRole("button", { name: "Approve" }));

    expect(await screen.findByText("There are no codes to bill")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Add your signature" })).not.toBeInTheDocument();
  });
});
