import { Table, Th } from "@/components/ui/Table";
import type { TeamMember } from "@/lib/api/types";
import { MemberRow, type MemberActions } from "./MemberRow";
import { TEAM_TEXT } from "./strings";

interface TeamTableProps extends MemberActions {
  members: TeamMember[];
  selfId: string | null;
}

export function TeamTable({ members, selfId, ...actions }: TeamTableProps) {
  const columns = TEAM_TEXT.columns;
  return (
    <Table label={TEAM_TEXT.tableLabel} minWidth="lg">
      <thead>
        <tr>
          <Th>{columns.name}</Th>
          <Th>{columns.role}</Th>
          <Th>{columns.twoStep}</Th>
          <Th>{columns.lastActive}</Th>
          <Th className="w-10">
            <span className="sr-only">{columns.more}</span>
          </Th>
        </tr>
      </thead>
      <tbody>
        {members.map((member) => (
          <MemberRow key={member.id} member={member} isSelf={member.id === selfId} {...actions} />
        ))}
      </tbody>
    </Table>
  );
}
