import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { verifySeal } from "@/lib/api/signatures";
import type { SealVerification } from "@/lib/api/types";
import { normalCode, sha256Hex } from "../fingerprint";
import { VerifyScreen } from "../VerifyScreen";

const navigation = vi.hoisted(() => ({ search: "", replace: vi.fn() }));

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(navigation.search),
  useRouter: () => ({ replace: navigation.replace, push: vi.fn() }),
}));
vi.mock("@/lib/api/signatures", () => ({ verifySeal: vi.fn() }));
vi.mock("../fingerprint", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../fingerprint")>()),
  sha256Hex: vi.fn(),
}));

const DOCUMENT = "a".repeat(64);
const VALID: SealVerification = {
  valid: true,
  problems: [],
  code: "ABCD-EFGH-JKMN",
  event: "approval",
  practice_name: "Lakeside",
  signer_kind: "user",
  signer_name: "Cora Coder",
  signer_title: "coder",
  signed_at: "2026-11-28T09:30:15.250000+00:00",
  document_sha256: DOCUMENT,
  envelope_sha256: "b".repeat(64),
};

beforeEach(() => {
  navigation.search = "";
});

describe("public verification", () => {
  it("checks the code from the link and shows the sealed facts", async () => {
    navigation.search = "?code=abcd efgh jkmn";
    vi.mocked(verifySeal).mockResolvedValue(VALID);

    render(<VerifyScreen />);

    const result = await screen.findByRole("region", { name: "Verification result" });
    expect(verifySeal).toHaveBeenCalledWith("ABCD-EFGH-JKMN");
    expect(within(result).getByText("Seal verified")).toBeInTheDocument();
    expect(within(result).getByText("Claim approved")).toBeInTheDocument();
    expect(within(result).getByText("Lakeside")).toBeInTheDocument();
    expect(within(result).getByText("Cora Coder (coder)")).toBeInTheDocument();
    expect(within(result).getByText(DOCUMENT)).toBeInTheDocument();
  });

  it("says which part no longer matches", async () => {
    navigation.search = "?code=ABCD-EFGH-JKMN";
    vi.mocked(verifySeal).mockResolvedValue({ ...VALID, valid: false, problems: ["record_changed", "seal_invalid"] });

    render(<VerifyScreen />);

    expect(await screen.findByText("Seal does not match")).toBeInTheDocument();
    expect(screen.getByText("The signed record changed")).toBeInTheDocument();
    expect(screen.getByText("The seal does not match")).toBeInTheDocument();
  });

  it("checks a typed code only when it is complete and puts it in the address", async () => {
    const user = userEvent.setup();
    render(<VerifyScreen />);
    const field = screen.getByRole("textbox", { name: "Verification code" });

    await user.type(field, "ABCD-EF");
    await user.tab();
    expect(screen.getByText("Enter the 12-character code.")).toBeInTheDocument();
    await user.clear(field);
    await user.type(field, "abcdefghjkmn");
    await user.click(screen.getByRole("button", { name: "Verify" }));

    expect(navigation.replace).toHaveBeenCalledWith("/verify?code=ABCD-EFGH-JKMN");
    expect(verifySeal).not.toHaveBeenCalled();
  });

  it("compares a chosen PDF with the signed document fingerprint in the browser", async () => {
    const user = userEvent.setup();
    navigation.search = "?code=ABCD-EFGH-JKMN";
    vi.mocked(verifySeal).mockResolvedValue(VALID);
    vi.mocked(sha256Hex).mockResolvedValueOnce(DOCUMENT).mockResolvedValueOnce("c".repeat(64));
    render(<VerifyScreen />);
    const input = await screen.findByLabelText("PDF to compare");

    await user.upload(input, new File(["%PDF-1.4"], "note.pdf", { type: "application/pdf" }));
    expect(await screen.findByText("Same as the signed document")).toBeInTheDocument();
    await user.upload(input, new File(["%PDF-1.5"], "other.pdf", { type: "application/pdf" }));
    expect(await screen.findByText("Not the signed document")).toBeInTheDocument();
  });
});

describe("verification codes", () => {
  it("are read without case, spaces or dashes and refuse ambiguous letters", () => {
    expect(normalCode(" abcd efgh jkmn ")).toBe("ABCD-EFGH-JKMN");
    expect(normalCode("ABCD-EFGH-JKM0")).toBeNull();
    expect(normalCode("ABCD-EFGH")).toBeNull();
  });
});
