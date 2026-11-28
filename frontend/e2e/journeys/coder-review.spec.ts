import { expect, test } from "@playwright/test";
import { SIGNATURE_TEXT } from "../../src/components/shared/signature/strings";
import { REVIEW_TEXT } from "../../src/features/note-review/strings";
import { QUEUE_TEXT } from "../../src/features/queue/strings";
import { TODAY_TEXT } from "../../src/features/today/strings";
import { LANE_LABELS } from "../../src/lib/labels";
import { expectAccessible } from "../support/accessibility";
import { heading } from "../support/app";
import { seed, type Account } from "../support/seed";
import { signIn } from "../support/signIn";

interface CoderDay {
  coder: Account;
  notes: { patient: string; id: string }[];
}

const FINDING = "[data-finding-key]";
const reasons = REVIEW_TEXT.override.reasons;

test("a coder decides findings by keyboard, edits billed codes, approves and moves to the next note", async ({ page }) => {
  const day = await seed<CoderDay>("coder-day");
  await signIn(page, day.coder);
  await expect(heading(page, TODAY_TEXT.title)).toBeVisible();

  await page.getByRole("link", { name: new RegExp(`^${LANE_LABELS.coder}\\s*,\\s*\\d`) }).click();
  await expect(page).toHaveURL(/\/queue\?lane=coder$/);
  await page.getByRole("link", { name: QUEUE_TEXT.reviewNext }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(new RegExp(day.notes.map((note) => note.patient).join("|")));
  const first = (await page.getByRole("heading", { level: 1 }).textContent()) ?? "";
  const next = day.notes.find((note) => note.patient !== first.trim());
  expect(next).toBeDefined();
  await expectAccessible(page);

  const current = page.locator(`${FINDING}[aria-current="true"]`);
  await expect(current).toContainText("99213");
  const key = (await current.getAttribute("data-finding-key")) ?? "";
  const visit = page.locator(`${FINDING}[data-finding-key="${key}"]`);
  await page.keyboard.press("j");
  await expect(visit).not.toHaveAttribute("aria-current", "true");
  await page.keyboard.press("k");
  await expect(visit).toHaveAttribute("aria-current", "true");

  await page.keyboard.press("n");
  const picker = page.getByRole("group", { name: new RegExp(`^${REVIEW_TEXT.override.label("")}`) });
  await expect(picker).toBeVisible();
  await page.keyboard.press("1");
  await expect(picker.getByRole("radio", { name: reasons.documentation })).toBeChecked();
  await page.keyboard.press("Enter");
  await expect(visit).toContainText(REVIEW_TEXT.override.given(reasons.documentation));

  await page.keyboard.press("k");
  await expect(visit).toHaveAttribute("aria-current", "true");
  await page.keyboard.press("y");
  await expect(visit.getByRole("radio", { name: REVIEW_TEXT.choices.accept })).toHaveAttribute("aria-checked", "true");
  const acceptSupported = page.getByRole("button", { name: REVIEW_TEXT.supported.accept });
  await expect(acceptSupported).toBeVisible();
  await page.keyboard.press("Shift+Y");
  await expect(acceptSupported).toBeHidden();

  await page.keyboard.press("e");
  const codes = page.getByRole("textbox", { name: REVIEW_TEXT.billed.label, exact: true });
  await codes.fill("99213, E11.65, I10");
  const billedReason = page.getByRole("group", { name: REVIEW_TEXT.override.label(REVIEW_TEXT.billed.subject) });
  await billedReason.getByRole("radio", { name: reasons.coding_guideline }).check();
  await page.getByRole("button", { name: REVIEW_TEXT.billed.save }).click();
  await expect(codes).toBeHidden();
  await expectAccessible(page);

  await page.keyboard.press("a");
  const signature = page.getByRole("dialog", { name: SIGNATURE_TEXT.addTitle });
  await expect(signature).toBeVisible();
  await expectAccessible(page);
  await signature.getByRole("radio", { name: SIGNATURE_TEXT.modes.typed }).click();
  await signature.getByRole("button", { name: SIGNATURE_TEXT.continue }).click();
  await signature.getByRole("button", { name: SIGNATURE_TEXT.adopt }).click();
  await expect(signature).toBeHidden();

  await expect(heading(page, next?.patient ?? "")).toBeVisible();
  await expect(page).toHaveURL(new RegExp(`/notes/${next?.id}`));
  await expect(page.getByText(REVIEW_TEXT.approvedToast(first.trim()))).toBeVisible();
});
