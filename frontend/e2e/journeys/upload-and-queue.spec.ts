import { expect, test, type Page } from "@playwright/test";
import { QUEUE_TEXT } from "../../src/features/queue/strings";
import { TODAY_TEXT } from "../../src/features/today/strings";
import { UPLOAD_TEXT } from "../../src/features/upload/strings";
import { LANE_LABELS } from "../../src/lib/labels";
import { expectAccessible } from "../support/accessibility";
import { heading, untilShown } from "../support/app";
import { dropFiles } from "../support/files";
import { seed, type Account } from "../support/seed";
import { signIn } from "../support/signIn";

interface UploadDay {
  coder: Account;
  provider: { name: string };
  files: string[];
  patients: [string, string];
}

function lane(page: Page, label: string) {
  return page.getByRole("radiogroup", { name: QUEUE_TEXT.laneFilter }).getByRole("radio", { name: new RegExp(`^${label}`) });
}

async function waitUntilRead(page: Page, patients: readonly string[]): Promise<void> {
  const table = page.getByRole("table", { name: QUEUE_TEXT.tableLabel });
  await untilShown(page, async () => {
    for (const patient of patients) {
      await expect(table.getByRole("link", { name: patient, exact: true })).toBeVisible({ timeout: 2_000 });
    }
  });
}

test("a coder drops the day's notes, page one matches them, and the queue opens one", async ({ page }) => {
  const day = await seed<UploadDay>("upload-day");
  const [changed, matching] = day.patients;

  await signIn(page, day.coder);
  await expect(heading(page, TODAY_TEXT.title)).toBeVisible();
  await dropFiles(page, day.files);
  await expect(page).toHaveURL(new RegExp("/upload$"));
  await expect(heading(page, UPLOAD_TEXT.title)).toBeVisible();
  await expect(page.getByText(UPLOAD_TEXT.files.reading)).toBeHidden();

  const files = page.getByRole("table", { name: UPLOAD_TEXT.files.label });
  for (const patient of day.patients) {
    const row = files.getByRole("row").filter({ hasText: patient });
    await expect(row).toContainText(UPLOAD_TEXT.status.ready);
    await expect(row.getByRole("combobox", { name: UPLOAD_TEXT.row.providerLabel(patient) })).toHaveText(
      UPLOAD_TEXT.plan.providerOption(day.provider.name, "MD"),
    );
  }
  await expect(page.getByText(UPLOAD_TEXT.files.ready(2))).toBeVisible();
  await expectAccessible(page);
  await page.getByRole("button", { name: UPLOAD_TEXT.bar.start(2) }).click();
  await expect(page.getByRole("status").filter({ hasText: UPLOAD_TEXT.done.accepted(2) })).toBeVisible();

  await page.goto("/queue");
  await expect(heading(page, QUEUE_TEXT.title)).toBeVisible();
  await waitUntilRead(page, day.patients);
  await expectAccessible(page);

  const table = page.getByRole("table", { name: QUEUE_TEXT.tableLabel });
  await lane(page, LANE_LABELS.coder).click();
  await expect(page).toHaveURL(/lane=coder/);
  await expect(table.getByRole("link", { name: changed, exact: true })).toBeVisible();
  await expect(table.getByRole("link", { name: matching, exact: true })).toBeHidden();
  await lane(page, LANE_LABELS.approve).click();
  await expect(table.getByRole("link", { name: matching, exact: true })).toBeVisible();
  await expect(table.getByRole("link", { name: changed, exact: true })).toBeHidden();

  const views = page.getByRole("radiogroup", { name: QUEUE_TEXT.views.label });
  await views.getByRole("radio", { name: QUEUE_TEXT.views.builtin.my_work }).click();
  await expect(page).toHaveURL(/assigned=me/);
  await expect(views.getByRole("radio", { name: QUEUE_TEXT.views.builtin.my_work })).toBeChecked();

  await lane(page, QUEUE_TEXT.all).click();
  await page.getByRole("combobox", { name: QUEUE_TEXT.assignedFilter }).click();
  await page.getByRole("option", { name: QUEUE_TEXT.anyone, exact: true }).click();
  await page.getByRole("button", { name: QUEUE_TEXT.views.save }).click();
  const save = page.getByRole("dialog", { name: QUEUE_TEXT.views.saveTitle });
  await save.getByLabel(QUEUE_TEXT.views.name, { exact: true }).fill("Synthetic day");
  await save.getByRole("button", { name: QUEUE_TEXT.views.saveConfirm, exact: true }).click();
  await expect(views.getByRole("radio", { name: "Synthetic day" })).toBeChecked();

  await table.getByRole("link", { name: changed, exact: true }).click();
  await expect(page).toHaveURL(new RegExp("/notes/"));
  await expect(heading(page, changed)).toBeVisible();
  await expectAccessible(page);
});
