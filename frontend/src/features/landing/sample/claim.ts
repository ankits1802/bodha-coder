import type { ClaimCodes, CodeKind, SampleFinding } from "./samples";

export type Decision = "accept" | "reject";
export type Decisions = Readonly<Record<string, Decision>>;

const LISTS: Record<CodeKind, keyof ClaimCodes> = { procedure: "procedures", diagnosis: "diagnoses" };

function applied(codes: readonly string[], finding: SampleFinding): string[] {
  if (finding.before === null) return [...codes, finding.after];
  return codes.map((code) => (code === finding.before ? finding.after : code));
}

export function claimCodes(billed: ClaimCodes, findings: readonly SampleFinding[], decisions: Decisions): ClaimCodes {
  return findings.reduce<ClaimCodes>((claim, finding) => {
    if (decisions[finding.key] !== "accept") return claim;
    const list = LISTS[finding.kind];
    return { ...claim, [list]: applied(claim[list], finding) };
  }, billed);
}

export function openCount(findings: readonly SampleFinding[], decisions: Decisions): number {
  return findings.filter((finding) => decisions[finding.key] === undefined).length;
}

export function nextOpen(findings: readonly SampleFinding[], decisions: Decisions, after: string): string | null {
  const start = findings.findIndex((finding) => finding.key === after);
  const ordered = [...findings.slice(start + 1), ...findings.slice(0, start + 1)];
  return ordered.find((finding) => decisions[finding.key] === undefined)?.key ?? null;
}
