import { readFile, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";

export type Who =
  | "admin"
  | "coder"
  | "cdi"
  | "compliance"
  | "biller"
  | "viewer"
  | "empty_admin"
  | "lapsed_admin"
  | "hq";

export type NoteKey = "approved" | "signed" | "ready" | "coder" | "provider" | "asked" | "compliance";

export interface Person {
  id: string;
  name: string;
  email: string;
  role: string;
  practice_id: string | null;
}

export interface Named {
  id: string;
  name: string;
}

export interface SeededNote {
  id: string;
  patient: string;
}

export interface SweepWorld {
  practice: Named;
  organization: Named;
  empty: Named;
  lapsed: Named;
  people: Record<Who, Person>;
  provider: { id: string; name: string; email: string; npi: string };
  notes: Record<NoteKey, SeededNote>;
  samples: { audit: string; training: string };
  verification_code: string;
  invitee: string;
}

const WORLD_FILE = path.join(os.tmpdir(), "bodha-e2e-sweep-world.json");

let loaded: Promise<SweepWorld> | null = null;

export async function keepWorld(world: SweepWorld): Promise<void> {
  await writeFile(WORLD_FILE, JSON.stringify(world), "utf8");
}

export function sweepWorld(): Promise<SweepWorld> {
  loaded ??= readFile(WORLD_FILE, "utf8").then((text) => JSON.parse(text) as SweepWorld);
  return loaded;
}
