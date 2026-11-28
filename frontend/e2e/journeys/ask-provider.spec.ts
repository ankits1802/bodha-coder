import { expect, test } from "@playwright/test";
import { SIGNATURE_TEXT } from "../../src/components/shared/signature/strings";
import { REVIEW_TEXT } from "../../src/features/note-review/strings";
import { RESPOND_TEXT } from "../../src/features/respond/strings";
import { TODAY_TEXT } from "../../src/features/today/strings";
import { expectAccessible } from "../support/accessibility";
import { heading, otherPerson, untilShown } from "../support/app";
import { linkIn, nextMessage } from "../support/mailbox";
import { seed, type Account } from "../support/seed";
import { signIn } from "../support/signIn";

interface ProviderDay {
  practice: string;
  coder: Account;
  provider: { name: string; email: string };
  note: { patient: string; id: string };
}

const ATTESTATION = "This is clinically accurate";
const MATCHES_HEADLINE = "Matches the note";
const CODE = new RegExp("\\b(\\d{6})\\b");

test("the coder asks the provider, who signs an addendum that the note is read again with", async ({ page, browser }) => {
  const day = await seed<ProviderDay>("provider-day");
  await signIn(page, day.coder);
  await expect(heading(page, TODAY_TEXT.title)).toBeVisible();

  await page.goto(`/notes/${day.note.id}?lane=provider&reason=questions`);
  await expect(heading(page, day.note.patient)).toBeVisible();
  await page.keyboard.press("q");
  const ask = page.getByRole("dialog", { name: REVIEW_TEXT.askDialog.title(day.provider.name) });
  await expect(ask).toBeVisible();
  await expectAccessible(page);
  await ask.getByRole("button", { name: REVIEW_TEXT.askDialog.send(1) }).click();
  await expect(ask).toBeHidden();
  await expect(page.getByText(REVIEW_TEXT.questions.requestStatus.sent)).toBeVisible();

  const questions = await nextMessage(day.provider.email, (message) => message.subject === `Questions from ${day.practice}`);
  const provider = await otherPerson(browser);
  await provider.goto(linkIn(questions, "/respond"));
  await expect(provider.getByRole("heading", { name: RESPOND_TEXT.verifyTitle })).toBeVisible();
  await expectAccessible(provider);
  await provider.getByRole("button", { name: RESPOND_TEXT.sendCode }).click();
  const codeMessage = await nextMessage(day.provider.email, (message) => message.subject === "Your verification code");
  await provider.getByLabel(RESPOND_TEXT.digitLabel(1), { exact: true }).fill(codeMessage.body.match(CODE)?.[1] ?? "");

  await expect(heading(provider, day.note.patient)).toBeVisible();
  await expectAccessible(provider);
  await provider.getByRole("radio", { name: "Controlled", exact: true }).check({ force: true });
  await provider.getByRole("radio", { name: SIGNATURE_TEXT.modes.typed }).click();
  await provider.getByRole("checkbox", { name: ATTESTATION }).check();
  await provider.getByRole("button", { name: RESPOND_TEXT.sign }).click();
  await expect(provider.getByRole("heading", { name: RESPOND_TEXT.signedTitle })).toBeVisible();
  await expectAccessible(provider);
  await provider.context().close();

  await untilShown(page, async () => {
    await expect(page.getByText(MATCHES_HEADLINE).first()).toBeVisible({ timeout: 2_000 });
  });
  const visitNote = page.getByRole("region", { name: REVIEW_TEXT.notePanel });
  await expect(visitNote.getByRole("heading", { name: new RegExp(`^${REVIEW_TEXT.addendumHeading("")}`) })).toBeVisible();
  await expect(page.getByText(REVIEW_TEXT.questions.requestStatus.answered).first()).toBeVisible();
  await expectAccessible(page);
});
