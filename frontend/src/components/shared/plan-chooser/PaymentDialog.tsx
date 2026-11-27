"use client";

import { useId, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { RadioOption } from "@/components/ui/RadioOption";
import type { BillingProvider } from "@/lib/api/types";
import { PLAN_CHOOSER_TEXT } from "./strings";

interface PaymentDialogProps {
  open: boolean;
  providers: readonly BillingProvider[];
  pending: boolean;
  error: string | null;
  onClose: () => void;
  onPay: (provider: BillingProvider) => void;
}

const words = PLAN_CHOOSER_TEXT.payWith;

export function PaymentDialog({ open, providers, pending, error, onClose, onPay }: PaymentDialogProps) {
  const group = useId();
  const [chosen, setChosen] = useState<BillingProvider | null>(null);
  const provider = chosen ?? providers[0] ?? null;
  const footer = (
    <>
      <Button variant="plain" onClick={onClose}>
        {words.cancel}
      </Button>
      <Button variant="primary" pending={pending} disabled={provider === null} onClick={() => provider && onPay(provider)}>
        {words.continue}
      </Button>
    </>
  );
  return (
    <Dialog open={open} onClose={onClose} title={words.title} footer={footer}>
      <fieldset className="m-0 flex min-w-0 flex-col gap-2 border-0 p-0">
        <legend className="sr-only">{words.label}</legend>
        {providers.map((option) => (
          <RadioOption key={option} name={group} value={option} checked={provider === option} onSelect={() => setChosen(option)}>
            <span>{PLAN_CHOOSER_TEXT.paidBy[option]}</span>
            {words.via[option] ? <span className="text-secondary">{words.via[option]}</span> : null}
          </RadioOption>
        ))}
      </fieldset>
      {error ? <InlineAlert tone="bad">{error}</InlineAlert> : null}
    </Dialog>
  );
}
