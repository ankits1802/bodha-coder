"use client";

import { AreaGuard } from "@/components/shared/AreaGuard";
import { SCOPE_ORDER } from "@/components/shared/shortcuts/registry";
import { ShortcutList } from "@/components/shared/shortcuts/ShortcutList";
import { PageHeader } from "@/components/ui/PageHeader";
import { Panel } from "@/components/ui/Panel";
import type { Role } from "@/lib/api/types";
import { useSession } from "@/lib/session/useSession";
import { helpSectionsFor } from "./helpSections";
import { HELP_TEXT, type HelpSectionKey } from "./strings";

function HelpSection({ section, role }: { section: HelpSectionKey; role: Role }) {
  const words = HELP_TEXT.sections[section];
  const headingId = `help-${section}`;
  return (
    <Panel aria-labelledby={headingId} className="max-w-180">
      <div className="flex flex-col gap-2.5 px-4.5 pt-4 pb-4.5">
        <h2 id={headingId} className="m-0 font-sans text-headline font-semibold tracking-headline">
          {words.title}
        </h2>
        {words.paragraphs.map((paragraph) => (
          <p key={paragraph} className="m-0 text-body text-label">
            {paragraph}
          </p>
        ))}
        {section === "shortcuts" ? <ShortcutList scopes={SCOPE_ORDER} role={role} /> : null}
      </div>
    </Panel>
  );
}

export function HelpScreen() {
  const { user } = useSession();
  return (
    <AreaGuard area="help">
      <PageHeader title={HELP_TEXT.title} />
      {user ? helpSectionsFor(user.role).map((section) => <HelpSection key={section} section={section} role={user.role} />) : null}
    </AreaGuard>
  );
}
