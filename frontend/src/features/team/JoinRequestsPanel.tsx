"use client";

import { useState } from "react";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { useAction } from "@/hooks/useAction";
import { useRemote } from "@/hooks/useRemote";
import { approveJoinRequest, declineJoinRequest, getJoinRequests } from "@/lib/api/domains";
import type { JoinRequestRow, PracticeRole } from "@/lib/api/types";
import { JoinRequestItem } from "./JoinRequestItem";
import { TEAM_TEXT } from "./strings";

export const JOIN_REQUESTS_KEY = "join-requests";

const words = TEAM_TEXT.requests;

function settle(task: () => Promise<unknown>): Promise<unknown> {
  return task();
}

export function JoinRequestsPanel({ onChanged }: { onChanged: () => void }) {
  const remote = useRemote(JOIN_REQUESTS_KEY, getJoinRequests);
  const action = useAction(settle);
  const [notice, setNotice] = useState<string | null>(null);

  async function run(task: () => Promise<unknown>, done: string): Promise<void> {
    setNotice(null);
    if (!(await action.run(task)).ok) return;
    setNotice(done);
    remote.reload();
    onChanged();
  }

  const approve = (request: JoinRequestRow, role: PracticeRole) =>
    void run(() => approveJoinRequest(request.id, role), words.approved(request.name));
  const decline = (request: JoinRequestRow) => void run(() => declineJoinRequest(request.id), words.declined(request.name));
  const requests = remote.state.status === "success" ? remote.state.data : [];
  const loadError = remote.state.status === "error" ? remote.state.error : null;

  if (requests.length === 0 && !notice && !loadError) return null;
  return (
    <Panel aria-label={words.title}>
      <PanelHeader title={words.title} />
      {loadError ? (
        <div className="px-4 pb-3">
          <InlineAlert tone="bad">{loadError}</InlineAlert>
        </div>
      ) : null}
      {notice ? (
        <div className="px-4 pb-3">
          <InlineAlert tone="ok">{notice}</InlineAlert>
        </div>
      ) : null}
      {action.error ? (
        <div className="px-4 pb-3">
          <InlineAlert tone="bad">{action.error}</InlineAlert>
        </div>
      ) : null}
      {requests.length > 0 ? (
        <ul aria-label={words.listLabel} className="m-0 list-none p-0">
          {requests.map((request) => (
            <JoinRequestItem key={request.id} request={request} busy={action.pending} onApprove={approve} onDecline={decline} />
          ))}
        </ul>
      ) : null}
    </Panel>
  );
}
