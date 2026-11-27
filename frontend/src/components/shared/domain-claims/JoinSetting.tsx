"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Select } from "@/components/ui/Select";
import { useAction } from "@/hooks/useAction";
import { setDomainJoin, type DomainScope } from "@/lib/api/domains";
import type { DomainClaim, DomainJoinMode, PracticeRole } from "@/lib/api/types";
import { AUTO_ROLE_OPTIONS, MODE_OPTIONS, joinRoleFor } from "./domainModel";
import { DOMAIN_TEXT } from "./strings";

interface JoinSettingProps {
  scope: DomainScope;
  claim: DomainClaim;
  onChanged: () => void;
}

const words = DOMAIN_TEXT;

export function JoinSetting({ scope, claim, onChanged }: JoinSettingProps) {
  const [mode, setMode] = useState<DomainJoinMode>(claim.join_mode);
  const [role, setRole] = useState<PracticeRole>(joinRoleFor("auto", claim.join_role));
  const [saved, setSaved] = useState(false);
  const save = useAction(setDomainJoin);
  const unchanged = mode === claim.join_mode && (mode !== "auto" || role === claim.join_role);

  async function submit(): Promise<void> {
    setSaved(false);
    const outcome = await save.run(scope, claim.id, { mode, role: mode === "auto" ? role : claim.join_role });
    if (!outcome.ok) return;
    setSaved(true);
    onChanged();
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-3">
        <Select
          variant="filter"
          label={words.joiningFor(claim.domain)}
          value={mode}
          options={MODE_OPTIONS}
          onChange={(next) => {
            setMode(next);
            setSaved(false);
          }}
        />
        {mode === "auto" ? (
          <Select variant="filter" label={words.roleFor(claim.domain)} value={role} options={AUTO_ROLE_OPTIONS} onChange={setRole} />
        ) : null}
        <Button size="sm" pending={save.pending} disabled={unchanged} onClick={() => void submit()}>
          {words.save}
        </Button>
        {saved ? <span role="status" className="text-subhead text-secondary">{words.saved}</span> : null}
      </div>
      {save.error ? <InlineAlert tone="bad">{save.error}</InlineAlert> : null}
    </div>
  );
}
