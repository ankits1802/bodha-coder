"use client";

import { useState } from "react";
import { useAction } from "@/hooks/useAction";
import { useRemote, type Remote } from "@/hooks/useRemote";
import { getOtherRequests, switchRequest } from "@/lib/api/respond";
import type { OtherRequest } from "@/lib/api/types";
import { watchExpiry } from "./providerSession";

export interface OtherRequests {
  remote: Remote<OtherRequest[]>;
  next: OtherRequest | null;
  openingId: string | null;
  error: string | null;
  open: (requestId: string) => void;
}

export function useOtherRequests(providerToken: string, onExpired: () => void, onSwitch: (token: string) => void): OtherRequests {
  const remote = useRemote(`respond-others:${providerToken}`, () => watchExpiry(getOtherRequests(providerToken), onExpired));
  const change = useAction((requestId: string) => watchExpiry(switchRequest(providerToken, requestId), onExpired));
  const [openingId, setOpeningId] = useState<string | null>(null);

  async function open(requestId: string): Promise<void> {
    setOpeningId(requestId);
    const outcome = await change.run(requestId);
    setOpeningId(null);
    if (outcome.ok) onSwitch(outcome.value.provider_token);
  }

  return {
    remote,
    next: remote.state.status === "success" ? (remote.state.data[0] ?? null) : null,
    openingId,
    error: change.error,
    open: (requestId) => void open(requestId),
  };
}
