import { MemberIdentity, MemberLastSeen, MemberTwoStep } from "@/components/shared/MemberCells";
import { MenuButton, type MenuItem } from "@/components/ui/MenuButton";
import { StatusDot } from "@/components/ui/StatusDot";
import { Table, Td, Th, Tr } from "@/components/ui/Table";
import type { HqTeamMember } from "@/lib/api/types";
import { HQ_TEXT } from "../strings";
import { STATUS_TONES, hqMemberActions, type HqMemberAction } from "./hqTeamModel";

const words = HQ_TEXT.team;

interface HqTeamTableProps {
  members: HqTeamMember[];
  selfId: string | null;
  onAction: (action: HqMemberAction, member: HqTeamMember) => void;
}

function menuFor(member: HqTeamMember, isSelf: boolean, onAction: HqTeamTableProps["onAction"]): MenuItem[] {
  return hqMemberActions(member, isSelf).map((action): MenuItem => ({
    key: action,
    label: words.menu[action],
    tone: action === "deactivate" ? "danger" : "default",
    onSelect: () => onAction(action, member),
  }));
}

function HqMemberRow({ member, isSelf, onAction }: { member: HqTeamMember; isSelf: boolean; onAction: HqTeamTableProps["onAction"] }) {
  return (
    <Tr>
      <Td>
        <MemberIdentity member={member} isSelf={isSelf} />
      </Td>
      <Td>
        <StatusDot tone={STATUS_TONES[member.status]}>{words.statuses[member.status]}</StatusDot>
      </Td>
      <Td>
        <MemberTwoStep member={member} />
      </Td>
      <Td>
        <MemberLastSeen member={member} />
      </Td>
      <Td className="w-10">
        <MenuButton label={words.moreFor(member.name)} items={menuFor(member, isSelf, onAction)} />
      </Td>
    </Tr>
  );
}

export function HqTeamTable({ members, selfId, onAction }: HqTeamTableProps) {
  const columns = words.columns;
  return (
    <Table label={words.tableLabel} minWidth="lg">
      <thead>
        <tr>
          <Th>{columns.name}</Th>
          <Th>{columns.status}</Th>
          <Th>{columns.twoStep}</Th>
          <Th>{columns.lastActive}</Th>
          <Th className="w-10">
            <span className="sr-only">{columns.more}</span>
          </Th>
        </tr>
      </thead>
      <tbody>
        {members.map((member) => (
          <HqMemberRow key={member.id} member={member} isSelf={member.id === selfId} onAction={onAction} />
        ))}
      </tbody>
    </Table>
  );
}
