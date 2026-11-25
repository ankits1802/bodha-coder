"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { Field } from "@/components/ui/Field";
import { TextArea } from "@/components/ui/Input";
import { COMPLIANCE_TEXT } from "../strings";

const FORM_ID = "compliance-keep-form";
const REASON_MIN = 3;

interface KeepDialogProps {
  open: boolean;
  pending: boolean;
  error: string | null;
  onClose: () => void;
  onKeep: (reason: string) => void;
}

export function KeepDialog({ open, pending, error, onClose, onKeep }: KeepDialogProps) {
  const [reason, setReason] = useState("");
  const ready = reason.trim().length >= REASON_MIN;
  const footer = (
    <>
      <Button onClick={onClose} disabled={pending}>
        {COMPLIANCE_TEXT.cancel}
      </Button>
      <Button type="submit" form={FORM_ID} variant="primary" pending={pending} disabled={!ready}>
        {COMPLIANCE_TEXT.keepSubmit}
      </Button>
    </>
  );
  return (
    <Dialog open={open} onClose={onClose} title={COMPLIANCE_TEXT.keepTitle} footer={footer}>
      <form
        id={FORM_ID}
        onSubmit={(event) => {
          event.preventDefault();
          if (ready) onKeep(reason.trim());
        }}
      >
        <Field label={COMPLIANCE_TEXT.keepReason} error={error}>
          {(control) => (
            <TextArea {...control} required maxLength={2000} value={reason} onChange={(event) => setReason(event.target.value)} />
          )}
        </Field>
      </form>
    </Dialog>
  );
}
