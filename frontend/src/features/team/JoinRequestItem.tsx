"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";
import type { JoinRequestRow, PracticeRole } from "@/lib/api/types";
import { ROLE_LABELS } from "@/lib/labels";
import { PRACTICE_ROLES } from "@/lib/roles";
import { TEAM_TEXT } from "./strings";

interface JoinRequestItemProps {
  request: JoinRequestRow;
  busy: boolean;
  onApprove: (request: JoinRequestRow, role: PracticeRole) => void;
  onDecline: (request: JoinRequestRow) => void;
}

const words = TEAM_TEXT.requests;
const ROLE_OPTIONS = PRACTICE_ROLES.map((role) => ({ value: role, label: ROLE_LABELS[role] }));

export function JoinRequestItem({ request, busy, onApprove, onDecline }: JoinRequestItemProps) {
  const [role, setRole] = useState<PracticeRole>(request.suggested_role);
  return (
    <li className="flex flex-wrap items-center justify-between gap-3 border-t border-hairline px-4 py-3">
      <div className="flex min-w-0 flex-col">
        <span className="text-body font-medium text-label">{request.name}</span>
        <span className="text-subhead break-all text-secondary">{words.from(request.email, request.domain)}</span>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <Select variant="filter" label={words.roleFor(request.name)} value={role} options={ROLE_OPTIONS} onChange={setRole} />
        <Button size="sm" disabled={busy} aria-label={words.approveFor(request.name)} onClick={() => onApprove(request, role)}>
          {words.approve}
        </Button>
        <Button variant="plain" size="sm" disabled={busy} aria-label={words.declineFor(request.name)} onClick={() => onDecline(request)}>
          {words.decline}
        </Button>
      </div>
    </li>
  );
}
