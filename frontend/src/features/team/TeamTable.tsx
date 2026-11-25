import { Table, Th } from "@/components/ui/Table";
import type { PracticeRole, TeamMember } from "@/lib/api/types";
import { MemberRow } from "./MemberRow";
import { TEAM_TEXT, type ConfirmKind, type SendKind } from "./strings";

interface TeamTableProps {
  members: TeamMember[];
  selfId: string | null;
  onRole: (member: TeamMember, role: PracticeRole) => void;
  onConfirm: (kind: ConfirmKind, member: TeamMember) => void;
  onSend: (kind: SendKind, member: TeamMember) => void;
}

export function TeamTable({ members, selfId, onRole, onConfirm, onSend }: TeamTableProps) {
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
          <MemberRow
            key={member.id}
            member={member}
            isSelf={member.id === selfId}
            onRole={onRole}
            onConfirm={onConfirm}
            onSend={onSend}
          />
        ))}
      </tbody>
    </Table>
  );
}
