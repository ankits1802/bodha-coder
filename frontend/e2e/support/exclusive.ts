import { open, rm, stat } from "node:fs/promises";
import os from "node:os";
import path from "node:path";

const RETRY_MS = 200;
const STALE_MS = 120_000;

function pause(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function claimed(file: string): Promise<boolean> {
  try {
    await (await open(file, "wx")).close();
    return true;
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== "EEXIST") throw error;
    return false;
  }
}

async function acquire(file: string): Promise<void> {
  while (!(await claimed(file))) {
    const held = await stat(file).catch(() => null);
    if (held && Date.now() - held.mtimeMs > STALE_MS) await rm(file, { force: true });
    await pause(RETRY_MS);
  }
}

export async function exclusively<T>(name: string, work: () => Promise<T>): Promise<T> {
  const file = path.join(os.tmpdir(), `bodha-e2e-${name}.lock`);
  await acquire(file);
  try {
    return await work();
  } finally {
    await rm(file, { force: true });
  }
}
