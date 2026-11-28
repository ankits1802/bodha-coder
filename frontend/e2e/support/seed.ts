import { execFile } from "node:child_process";
import path from "node:path";
import { promisify } from "node:util";
import { TOUR_VERSION } from "../../src/components/shared/tour/tourSteps";

const run = promisify(execFile);
const BACKEND = path.resolve(__dirname, "../../../backend");
const SEED_TIMEOUT_MS = 180_000;

export interface Account {
  id: string;
  name: string;
  email: string;
  password: string;
  role: string;
  two_step_secret: string | null;
}

export async function seed<T>(scenario: string): Promise<T> {
  const python = process.env.E2E_PYTHON ?? "python";
  const argumentsList = ["-m", "tests.e2e_seed", scenario, "--tour-version", String(TOUR_VERSION)];
  try {
    const { stdout } = await run(python, argumentsList, { cwd: BACKEND, timeout: SEED_TIMEOUT_MS, maxBuffer: 1 << 20 });
    const lines = stdout.trim().split("\n");
    return JSON.parse(lines.at(-1) ?? "") as T;
  } catch (error) {
    const failure = error as { stderr?: string; message: string };
    throw new Error(`seeding ${scenario} failed: ${failure.stderr || failure.message}`);
  }
}
