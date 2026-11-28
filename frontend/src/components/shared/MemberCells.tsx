import { Avatar } from "@/components/ui/Avatar";
import { EmptyValue } from "@/components/ui/EmptyValue";
import { StatusDot } from "@/components/ui/StatusDot";
import type { TeamMember } from "@/lib/api/types";
import { FORMAT_WORDS, formatSince } from "@/lib/format";
import { SHARED_TEXT } from "./strings";

export type MemberFacts = Pick<TeamMember, "name" | "email" | "status" | "mfa_enabled" | "last_active_at">;

export function MemberIdentity({ member, isSelf }: { member: MemberFacts; isSelf: boolean }) {
  const blocked = member.status === "blocked";
  return (
    <span className="flex items-center gap-3">
      <Avatar name={member.name} size="md" muted={blocked} />
      <span className={blocked ? "opacity-60" : ""}>
        <span className="font-medium">{member.name}</span>
        {isSelf ? <span className="ml-1.5 text-footnote text-tertiary">{SHARED_TEXT.member.you}</span> : null}
        <span className="block text-footnote text-secondary">{member.email}</span>
      </span>
    </span>
  );
}

export function MemberLastSeen({ member }: { member: MemberFacts }) {
  return <span className="text-secondary">{member.last_active_at ? formatSince(member.last_active_at) : FORMAT_WORDS.empty}</span>;
}

export function MemberTwoStep({ member }: { member: MemberFacts }) {
  if (member.status !== "active") return <EmptyValue />;
  return member.mfa_enabled ? (
    <StatusDot tone="ok">{SHARED_TEXT.member.twoStepOn}</StatusDot>
  ) : (
    <StatusDot tone="warn">{SHARED_TEXT.member.twoStepOff}</StatusDot>
  );
}
