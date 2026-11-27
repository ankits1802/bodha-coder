import type { PracticeSetup, SetupSection, TeamList, TeamMember } from "@/lib/api/types";

function section(complete: boolean): SetupSection {
  return { fields: [], values: {}, complete };
}

export const ADMIN_MEMBER: TeamMember = {
  id: "user-1",
  name: "Morgan Ellis",
  email: "morgan@harbor.example.com",
  role: "admin",
  status: "active",
  mfa_enabled: true,
  last_active_at: null,
};

export function setupWith(changes: { providers?: boolean; payer?: boolean; checks?: boolean; security?: boolean; dismissed?: boolean } = {}): PracticeSetup {
  return {
    sections: { providers: section(changes.providers ?? false) },
    complete: 0,
    total: 12,
    checks: { em: true, icd: true, cdi: true, audit: true, mips: false, hcc: false },
    missing_npi: 0,
    payers: changes.payer ? [{ id: "payer-1", name: "Medicare Part B", payer_id: "SMTX1", plan_type: "medicare", active: true }] : [],
    security: { mfa_roles: ["admin", "compliance"], idle_minutes: 15, access_log_years: 7 },
    review: { confirm_level_changes: false, hold_until_confirmed: false },
    first_run: { checks: changes.checks ?? false, security: changes.security ?? false, dismissed: changes.dismissed ?? false },
  } as unknown as PracticeSetup;
}

export function teamOf(count: number): TeamList {
  const others = Array.from({ length: count - 1 }, (_, index) => ({ ...ADMIN_MEMBER, id: `user-${index + 2}`, role: "coder" as const }));
  return { seats: 10, members: [ADMIN_MEMBER, ...others] };
}
