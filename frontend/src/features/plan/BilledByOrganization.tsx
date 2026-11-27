import { ButtonLink } from "@/components/ui/ButtonLink";
import { Panel } from "@/components/ui/Panel";
import type { PayerOrganization } from "@/lib/api/types";
import { organizationPath } from "@/lib/paths";
import { useSession } from "@/lib/session/useSession";
import { PLAN_TEXT } from "./strings";

const words = PLAN_TEXT.billedBy;

export function BilledByOrganization({ organization }: { organization: PayerOrganization }) {
  const admins = useSession().user?.organizations ?? [];
  const isAdmin = admins.some((choice) => choice.id === organization.id);
  return (
    <Panel aria-label={words.label} className="p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="m-0 text-body">{words.title(organization.name)}</p>
        {isAdmin ? (
          <ButtonLink variant="primary" href={organizationPath(organization.id, "plan")}>
            {words.open(organization.name)}
          </ButtonLink>
        ) : null}
      </div>
    </Panel>
  );
}
