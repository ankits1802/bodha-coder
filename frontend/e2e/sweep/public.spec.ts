import { LEGAL_SLUGS, legalPath } from "../../src/components/shared/legal/legalLinks";
import { RESPOND_TEXT } from "../../src/features/respond/strings";
import { VERIFY_TEXT } from "../../src/features/verify/strings";
import { expectAccessible } from "../support/accessibility";
import { ADMIN_ORIGIN, SITE_ORIGIN } from "../support/app";
import { exclusively } from "../support/exclusive";
import { linkIn, messageCount, nextMessage, type Message } from "../support/mailbox";
import { test } from "./fixtures";
import { expectPrimaryByKeyboard, settle, sweep } from "./visit";
import { sweepWorld } from "./world";

const PUBLIC_PATHS = [
  "/",
  "/pricing",
  "/legal",
  ...LEGAL_SLUGS.map(legalPath),
  "/sign-in",
  "/forgot-password",
  "/set-password",
  "/sign-up",
  "/sign-up/join",
  "/sign-up/practice",
  "/verify",
  "/verify-domain",
];
const CODE = new RegExp("\\b(\\d{6})\\b");

function isCode(message: Message): boolean {
  return message.subject === "Your verification code";
}

for (const path of PUBLIC_PATHS) {
  test(`public ${path}`, async ({ page }) => {
    await sweep(page, SITE_ORIGIN, { path });
  });
}

test("public page that does not exist", async ({ page }) => {
  await sweep(page, SITE_ORIGIN, { path: "/no-such-page" });
});

test("HQ sign-in on its own host", async ({ page }) => {
  await sweep(page, ADMIN_ORIGIN, { path: "/sign-in" });
});

test("verify page with a valid code", async ({ page }) => {
  const world = await sweepWorld();
  await sweep(page, SITE_ORIGIN, {
    path: `/verify?code=${encodeURIComponent(world.verification_code)}`,
    ready: (shown) => shown.getByRole("region", { name: VERIFY_TEXT.resultLabel }).getByRole("status"),
  });
});

test("set-password from an invitation", async ({ page }) => {
  const world = await sweepWorld();
  const invite = await nextMessage(world.invitee, (message) => message.subject === `Join ${world.empty.name} on Bodha Assure`);
  const link = new URL(linkIn(invite, "/set-password"));
  await sweep(page, SITE_ORIGIN, { path: `${link.pathname}${link.search}${link.hash}` });
});

test("provider respond link, before and after the code", async ({ page }) => {
  const world = await sweepWorld();
  const questions = await nextMessage(world.provider.email, (message) => message.subject === `Questions from ${world.practice.name}`);
  const link = new URL(linkIn(questions, "/respond"));
  await sweep(page, SITE_ORIGIN, {
    path: `${link.pathname}${link.search}${link.hash}`,
    ready: (shown) => shown.getByRole("heading", { level: 1, name: RESPOND_TEXT.verifyTitle }),
  });
  await exclusively("provider-code", async () => {
    const before = await messageCount(world.provider.email, isCode);
    await page.getByRole("button", { name: RESPOND_TEXT.sendCode }).click();
    const code = await nextMessage(world.provider.email, isCode, before);
    await page.getByLabel(RESPOND_TEXT.digitLabel(1), { exact: true }).fill(code.body.match(CODE)?.[1] ?? "");
    await settle(page, page.getByRole("heading", { level: 1, name: world.notes.asked.patient }));
  });
  await expectAccessible(page);
  await expectPrimaryByKeyboard(page);
});
