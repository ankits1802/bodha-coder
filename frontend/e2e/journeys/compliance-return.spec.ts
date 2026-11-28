import { expect, test } from "@playwright/test";
import { SHARED_TEXT } from "../../src/components/shared/strings";
import { COMPLIANCE_TEXT } from "../../src/features/compliance/strings";
import { INBOX_TEXT } from "../../src/features/inbox/strings";
import { REVIEW_TEXT } from "../../src/features/note-review/strings";
import { TODAY_TEXT } from "../../src/features/today/strings";
import { RETURN_REASON_LABELS } from "../../src/lib/labels";
import { expectAccessible } from "../support/accessibility";
import { heading, otherPerson } from "../support/app";
import { seed, type Account } from "../support/seed";
import { signIn } from "../support/signIn";

interface ComplianceDay {
  officer: Account;
  coder: Account;
  note: { patient: string; id: string };
}

const RETURN_NOTE = "The plan does not support this level";
const reason = RETURN_REASON_LABELS.level_not_supported;

test("compliance returns a note with a reason and the coder finds it in the inbox", async ({ page, browser }) => {
  const day = await seed<ComplianceDay>("compliance-day");
  await signIn(page, day.officer);
  await expect(heading(page, COMPLIANCE_TEXT.title)).toBeVisible();
  const featured = page.getByRole("article", { name: day.note.patient });
  await expect(featured).toBeVisible();
  await expectAccessible(page);

  await featured.getByRole("button", { name: COMPLIANCE_TEXT.returnToCoder }).click();
  const dialog = page.getByRole("dialog", { name: SHARED_TEXT.returnDialog.title });
  await dialog.getByRole("radio", { name: reason, exact: true }).check();
  await dialog.getByRole("textbox").fill(RETURN_NOTE);
  await expectAccessible(page);
  await dialog.getByRole("button", { name: SHARED_TEXT.returnDialog.submit }).click();
  await expect(page.getByRole("status").filter({ hasText: COMPLIANCE_TEXT.decided.return })).toBeVisible();

  const coder = await otherPerson(browser);
  await signIn(coder, day.coder);
  await expect(heading(coder, TODAY_TEXT.title)).toBeVisible();
  await coder.goto("/inbox");
  await expect(heading(coder, INBOX_TEXT.title)).toBeVisible();
  const item = coder
    .getByRole("list", { name: INBOX_TEXT.listLabel })
    .getByRole("link", { name: new RegExp(INBOX_TEXT.sentences.complianceReturned(day.officer.name, reason)) });
  await expect(item).toBeVisible();
  await expectAccessible(coder);
  await item.click();
  await expect(coder).toHaveURL(new RegExp(`/notes/${day.note.id}`));
  await expect(coder.getByText(REVIEW_TEXT.returned(reason, day.officer.name))).toBeVisible();
  await expectAccessible(coder);
  await coder.context().close();
});
