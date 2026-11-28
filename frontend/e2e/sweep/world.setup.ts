import { test as setup } from "@playwright/test";
import { seed } from "../support/seed";
import { keepWorld, type SweepWorld } from "./world";

const SEED_TIMEOUT_MS = 240_000;

setup("seed the practices, people and notes every sweep visit reads", async () => {
  setup.setTimeout(SEED_TIMEOUT_MS);
  await keepWorld(await seed<SweepWorld>("sweep-day"));
});
