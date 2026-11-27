import type { Finding, NoteDetail, QueuePage } from "@/lib/api/types";

export function finding(overrides: Partial<Finding>): Finding {
  return {
    kind: "diagnosis",
    key: "dx:I10",
    action: "keep",
    title: "Hypertension",
    reasoning: "",
    code_before: "I10",
    code_after: null,
    evidence: [],
    severity: null,
    detail: {},
    default_choice: "keep",
    choice: "keep",
    allowed: ["keep"],
    departing_choices: [],
    override: null,
    override_needed: false,
    decided: false,
    decide_again: false,
    amount_change: null,
    ...overrides,
  };
}

export function noteDetail(findings: Finding[], overrides: Partial<NoteDetail> = {}): NoteDetail {
  return {
    note: { id: "note-1", status: "ready", lane: "coder", lane_reason: "code_changes", returned: null, flag_reason: null },
    findings,
    requests: [],
    texts: [],
    claim: [],
    estimate: null,
    analysis: null,
    history: { analyses: [], code_sets: [], decisions: [], changes: [], snapshots: [], exports: [], attestations: [], returns: [] },
    ...overrides,
  } as unknown as NoteDetail;
}

const NO_WORK = { total: 0, due_soon: 0 };

export function queueTotals(lanes: Partial<Record<keyof QueuePage["lanes"], number>>, reasons: Partial<Record<keyof QueuePage["provider_reasons"], number>> = {}) {
  const count = (total: number | undefined) => (total ? { total, due_soon: 0 } : NO_WORK);
  return {
    lanes: { approve: count(lanes.approve), coder: count(lanes.coder), provider: count(lanes.provider), compliance: count(lanes.compliance) },
    provider_reasons: { questions: count(reasons.questions), waiting_on_provider: count(reasons.waiting_on_provider) },
  };
}
