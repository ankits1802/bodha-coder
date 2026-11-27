"use client";

import { useRemote } from "@/hooks/useRemote";
import { getTeam } from "@/lib/api/team";
import type { TeamList, User } from "@/lib/api/types";
import { canDo, canUse } from "@/lib/roles";

export interface Assignee {
  id: string;
  name: string;
}

export interface Assignees {
  people: Assignee[];
  error: string | null;
}

const NONE: Assignees = { people: [], error: null };

function noteReaders(team: TeamList): Assignee[] {
  return team.members
    .filter((member) => member.status === "active" && canUse(member.role, "queue"))
    .map((member) => ({ id: member.id, name: member.name }));
}

export function useAssignees(user: User | null): Assignees {
  const anyone = canDo(user?.role, "assignAnyone");
  const team = useRemote(anyone ? "assignees" : null, getTeam);
  if (!user || !canDo(user.role, "assign")) return NONE;
  if (!anyone) return { people: [{ id: user.id, name: user.name }], error: null };
  if (team.state.status === "error") return { people: [], error: team.state.error };
  return team.state.status === "success" ? { people: noteReaders(team.state.data), error: null } : NONE;
}
