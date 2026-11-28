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

export interface SessionHolder {
  id: string;
  practice_id: string | null;
}

export interface OpenedSessions {
  cookie: { name: string; path: string };
  tokens: string[];
}

async function backendJson<T>(module: string, argumentsList: readonly string[], what: string): Promise<T> {
  const python = process.env.E2E_PYTHON ?? "python";
  try {
    const { stdout } = await run(python, ["-m", module, ...argumentsList], {
      cwd: BACKEND,
      timeout: SEED_TIMEOUT_MS,
      maxBuffer: 1 << 20,
    });
    const lines = stdout.trim().split("\n");
    return JSON.parse(lines.at(-1) ?? "") as T;
  } catch (error) {
    const failure = error as { stderr?: string; message: string };
    throw new Error(`${what} failed: ${failure.stderr || failure.message}`);
  }
}

export function seed<T>(scenario: string): Promise<T> {
  return backendJson<T>("tests.e2e_seed", [scenario, "--tour-version", String(TOUR_VERSION)], `seeding ${scenario}`);
}

export function openSessions(holders: readonly SessionHolder[]): Promise<OpenedSessions> {
  const people = holders.map((holder) => (holder.practice_id ? `${holder.id}:${holder.practice_id}` : holder.id));
  return backendJson<OpenedSessions>("tests.e2e_seed.sessions", people, "opening sessions");
}
