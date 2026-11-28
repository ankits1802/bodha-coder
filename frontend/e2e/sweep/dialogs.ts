import type { Locator, Page } from "@playwright/test";
import { expectAccessible } from "../support/accessibility";
import { expectFocusReturned, expectFocusTrapped, openByKeyboard } from "../support/keyboard";
import { originFor } from "./fixtures";
import { open, settle } from "./visit";
import { sweepWorld, type SweepWorld, type Who } from "./world";

type Find = (page: Page, world: SweepWorld) => Locator;

export interface DialogCase {
  name: string;
  who: Who;
  path: (world: SweepWorld) => string;
  ready?: Find;
  before?: (page: Page) => Promise<void>;
  trigger: Find;
  dialog: Find;
  inside?: (page: Page, dialog: Locator) => Promise<void>;
}

export function escaped(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

export function startingWith(text: string): RegExp {
  return new RegExp(`^${escaped(text)}`);
}

export async function checkDialog(page: Page, shown: DialogCase): Promise<void> {
  const world = await sweepWorld();
  const ready = shown.ready;
  await open(page, originFor(shown.who), {
    path: shown.path(world),
    ready: ready ? (current) => ready(current, world) : undefined,
  });
  await shown.before?.(page);
  const trigger = shown.trigger(page, world);
  const dialog = shown.dialog(page, world);
  await openByKeyboard(page, trigger, dialog);
  await settle(page, dialog, dialog);
  await expectAccessible(page);
  await expectFocusTrapped(page, dialog);
  await shown.inside?.(page, dialog);
  await expectFocusReturned(page, dialog, trigger);
}
