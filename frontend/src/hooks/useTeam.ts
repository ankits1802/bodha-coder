"use client";

import { getTeam } from "@/lib/api/team";
import type { TeamList } from "@/lib/api/types";
import { useRemote, type Remote } from "./useRemote";

export const TEAM_KEY = "team";

export function useTeam(enabled = true): Remote<TeamList> {
  return useRemote(enabled ? TEAM_KEY : null, getTeam);
}
