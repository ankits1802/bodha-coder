import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { draftFrom } from "@/components/shared/signature/signatureImage";
import { draftProviderSignature } from "@/lib/api/signatures";
import type { AddendumQuestion } from "@/lib/api/types";
import { AnswerForm } from "../AnswerForm";
import type { ProviderSigning } from "../useProviderSigning";
import { SAVED_SIGNATURE } from "./signatureFixture";

vi.mock("@/lib/api/signatures", () => ({ draftProviderSignature: vi.fn() }));
vi.mock("@/components/shared/signature/signatureImage", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/components/shared/signature/signatureImage")>()),
  draftFrom: vi.fn(),
}));

const QUESTIONS: AddendumQuestion[] = [
  { key: "dx:N18.30", text: "What stage is the kidney disease?", context: [], options: ["Stage 3a", "Other"] },
];
const BODY = { source: "typed" as const, typed_name: "Elena Varga", image: SAVED_SIGNATURE.image };

function renderForm(remembered = SAVED_SIGNATURE as typeof SAVED_SIGNATURE | null) {
  const onSign = vi.fn();
  render(
    <AnswerForm
      questions={QUESTIONS}
      providerName="Elena Varga, MD"
      attestation="This is clinically accurate"
      pending={false}
      error={null}
      remembered={remembered}
      onSign={onSign}
    />,
  );
  return { onSign, sign: () => screen.getByRole("button", { name: "Sign and add to note" }) };
}

async function answerAndConfirm(user: ReturnType<typeof userEvent.setup>): Promise<void> {
  const group = screen.getByRole("group", { name: /What stage is the kidney disease/ });
  await user.click(within(group).getByRole("radio", { name: "Stage 3a" }));
  await user.click(screen.getByRole("checkbox", { name: "This is clinically accurate" }));
}

function signingOf(onSign: ReturnType<typeof vi.fn>): ProviderSigning {
  return onSign.mock.calls[0]?.[1] as ProviderSigning;
}

beforeEach(() => {
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
});

describe("provider signing on the secure link", () => {
  it("needs a signature before the addendum can be signed and can remember it", async () => {
    const user = userEvent.setup();
    vi.mocked(draftFrom).mockResolvedValue(BODY);
    vi.mocked(draftProviderSignature).mockResolvedValue({ ...SAVED_SIGNATURE, id: "signature-2", source: "typed" });
    const form = renderForm(null);
    await answerAndConfirm(user);
    expect(form.sign()).toBeDisabled();

    screen.getByRole("radio", { name: "Draw" }).focus();
    await user.keyboard("{ArrowRight}");
    expect(screen.getByRole("img", { name: "Signature: Elena Varga" })).toBeInTheDocument();
    await user.click(screen.getByRole("checkbox", { name: "Remember my signature for this practice" }));
    expect(form.sign()).toBeEnabled();
    await user.click(form.sign());

    const choice = await signingOf(form.onSign).choose("provider-token");
    expect(draftProviderSignature).toHaveBeenCalledWith("provider-token", BODY);
    expect(choice).toEqual({ signature_id: "signature-2", remember_signature: true });
  });

  it("signs with the remembered signature without sending a new one", async () => {
    const user = userEvent.setup();
    const form = renderForm();
    expect(screen.getByRole("img", { name: "Signature of Elena Varga" })).toBeInTheDocument();
    await answerAndConfirm(user);
    await user.click(form.sign());

    const choice = await signingOf(form.onSign).choose("provider-token");
    expect(choice).toEqual({ signature_id: null, remember_signature: false });
    expect(draftProviderSignature).not.toHaveBeenCalled();
  });

  it("lets the provider sign with a new signature instead of the remembered one", async () => {
    const user = userEvent.setup();
    const form = renderForm();
    await answerAndConfirm(user);

    await user.click(screen.getByRole("button", { name: "Use a new signature" }));

    expect(screen.getByRole("img", { name: "Signature pad, empty" })).toBeInTheDocument();
    expect(form.sign()).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Use my saved signature" }));
    expect(form.sign()).toBeEnabled();
  });
});
