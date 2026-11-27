import { Avatar } from "@/components/ui/Avatar";
import { MenuButton, type MenuItem } from "@/components/ui/MenuButton";
import { Select } from "@/components/ui/Select";
import { StatusDot } from "@/components/ui/StatusDot";
import { Td, Tr } from "@/components/ui/Table";
import type { PracticeRole, TeamMember } from "@/lib/api/types";
import { FORMAT_WORDS, formatSince } from "@/lib/format";
import { MEMBER_STATUS_LABELS, ROLE_LABELS } from "@/lib/labels";
import { PRACTICE_ROLES } from "@/lib/roles";
import { TEAM_TEXT, type ConfirmKind, type SendKind } from "./strings";

interface MemberRowProps {
  member: TeamMember;
  isSelf: boolean;
  onRole: (member: TeamMember, role: PracticeRole) => void;
  onConfirm: (kind: ConfirmKind, member: TeamMember) => void;
  onSend: (kind: SendKind, member: TeamMember) => void;
}

function menuFor(member: TeamMember, props: Pick<MemberRowProps, "onConfirm" | "onSend">): MenuItem[] {
  const words = TEAM_TEXT.menu;
  const items: MenuItem[] = [];
  if (member.mfa_enabled) items.push({ key: "reset", label: words.reset, onSelect: () => props.onConfirm("reset", member) });
  if (member.status === "invited") items.push({ key: "resend", label: words.resend, onSelect: () => props.onSend("invite", member) });
  if (member.status === "active") items.push({ key: "password", label: words.passwordReset, onSelect: () => props.onSend("password", member) });
  if (member.status === "blocked") items.push({ key: "unblock", label: words.unblock, onSelect: () => props.onConfirm("unblock", member) });
  else items.push({ key: "block", label: words.block, tone: "danger", onSelect: () => props.onConfirm("block", member) });
  return items;
}

function LastActive({ member }: { member: TeamMember }) {
  if (member.status === "invited") return <StatusDot tone="neutral">{MEMBER_STATUS_LABELS.invited}</StatusDot>;
  if (member.status === "blocked") return <StatusDot tone="bad">{MEMBER_STATUS_LABELS.blocked}</StatusDot>;
  return <span className="text-secondary">{member.last_active_at ? formatSince(member.last_active_at) : FORMAT_WORDS.empty}</span>;
}

function TwoStep({ member }: { member: TeamMember }) {
  if (member.status !== "active") return <span className="text-quaternary">{FORMAT_WORDS.empty}</span>;
  return member.mfa_enabled ? (
    <StatusDot tone="ok">{TEAM_TEXT.twoStepOn}</StatusDot>
  ) : (
    <StatusDot tone="warn">{TEAM_TEXT.twoStepOff}</StatusDot>
  );
}

export function MemberRow({ member, isSelf, onRole, onConfirm, onSend }: MemberRowProps) {
  const blocked = member.status === "blocked";
  const editable = !isSelf && !blocked && member.role !== "hq";
  return (
    <Tr>
      <Td>
        <span className="flex items-center gap-3">
          <Avatar name={member.name} size="md" muted={blocked} />
          <span className={blocked ? "opacity-60" : ""}>
            <span className="font-medium">{member.name}</span>
            {isSelf ? <span className="ml-1.5 text-footnote text-tertiary">{TEAM_TEXT.you}</span> : null}
            <span className="block text-footnote text-secondary">{member.email}</span>
          </span>
        </span>
      </Td>
      <Td>
        {editable ? (
          <Select<PracticeRole>
            variant="inline"
            label={TEAM_TEXT.roleFor(member.name)}
            value={member.role as PracticeRole}
            options={PRACTICE_ROLES.map((role) => ({ value: role, label: ROLE_LABELS[role] }))}
            onChange={(role) => onRole(member, role)}
          />
        ) : (
          <span className="px-2 text-callout text-secondary">{ROLE_LABELS[member.role]}</span>
        )}
      </Td>
      <Td>
        <TwoStep member={member} />
      </Td>
      <Td>
        <LastActive member={member} />
      </Td>
      <Td className="w-10">
        <MenuButton label={TEAM_TEXT.moreFor(member.name)} items={menuFor(member, { onConfirm, onSend })} disabled={isSelf} />
      </Td>
    </Tr>
  );
}
