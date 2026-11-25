"use client";

import { useSyncExternalStore } from "react";
import { getServerSession, getSession, subscribeSession, type SessionState } from "./store";

export function useSession(): SessionState {
  return useSyncExternalStore(subscribeSession, getSession, getServerSession);
}
