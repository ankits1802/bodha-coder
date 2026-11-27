import { ButtonLink } from "@/components/ui/ButtonLink";
import type { Role } from "@/lib/api/types";
import { canUse } from "@/lib/roles";
import { TODAY_TEXT } from "../strings";
import type { TodayStart } from "../todayStart";

interface TodayActionsProps {
  role: Role;
  start: TodayStart | null;
  uploadLeads: boolean;
}

export function TodayActions({ role, start, uploadLeads }: TodayActionsProps) {
  return (
    <>
      {canUse(role, "upload") ? (
        <ButtonLink href="/upload" variant={uploadLeads ? "primary" : "secondary"}>
          {TODAY_TEXT.upload}
        </ButtonLink>
      ) : null}
      {start ? (
        <ButtonLink href={start.href} variant="primary">
          {TODAY_TEXT.start[start.kind]}
        </ButtonLink>
      ) : null}
    </>
  );
}
