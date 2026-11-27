"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { useAction } from "@/hooks/useAction";
import { claimDomain, type DomainScope } from "@/lib/api/domains";
import type { PracticeOption } from "./domainModel";
import { DOMAIN_TEXT } from "./strings";

interface ClaimFormProps {
  scope: DomainScope;
  practices?: readonly PracticeOption[];
  onClaimed: () => void;
}

const words = DOMAIN_TEXT;

export function ClaimForm({ scope, practices, onClaimed }: ClaimFormProps) {
  const [domain, setDomain] = useState("");
  const [practiceId, setPracticeId] = useState(practices?.[0]?.id ?? "");
  const claim = useAction(claimDomain);

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const body = practices ? { domain: domain.trim(), practice_id: practiceId } : { domain: domain.trim() };
    if (!(await claim.run(scope, body)).ok) return;
    setDomain("");
    onClaimed();
  }

  return (
    <form onSubmit={(event) => void submit(event)} noValidate className="flex flex-wrap items-end gap-3 px-4 pb-4">
      <Field label={words.domain} error={claim.error} className="min-w-56 flex-1">
        {(control) => (
          <Input
            {...control}
            value={domain}
            autoComplete="off"
            spellCheck={false}
            onChange={(event) => {
              setDomain(event.target.value);
              claim.clearError();
            }}
          />
        )}
      </Field>
      {practices ? (
        <Field label={words.practice} className="min-w-56 flex-1">
          {(control) => (
            <Select
              {...control}
              value={practiceId}
              options={practices.map((practice) => ({ value: practice.id, label: practice.name }))}
              onChange={setPracticeId}
            />
          )}
        </Field>
      ) : null}
      <Button type="submit" pending={claim.pending} disabled={domain.trim().length === 0 || (practices !== undefined && !practiceId)}>
        {words.claim}
      </Button>
    </form>
  );
}
