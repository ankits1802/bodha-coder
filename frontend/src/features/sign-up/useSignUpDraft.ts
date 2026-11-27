"use client";

import { useState } from "react";
import { signUpErrors, type SignUpDraft, type SignUpErrors, type SignUpField } from "./signUpDraft";

export interface DraftForm {
  draft: SignUpDraft;
  errors: SignUpErrors;
  change: <F extends SignUpField>(field: F, value: SignUpDraft[F]) => void;
  touch: (field: SignUpField) => void;
  checkAll: () => boolean;
}

export function useSignUpDraft(initial: SignUpDraft, fields: readonly SignUpField[]): DraftForm {
  const [draft, setDraft] = useState(initial);
  const [touched, setTouched] = useState<readonly SignUpField[]>([]);

  function touch(field: SignUpField): void {
    setTouched((current) => (current.includes(field) ? current : [...current, field]));
  }

  function checkAll(): boolean {
    setTouched(fields);
    return Object.keys(signUpErrors(draft, fields)).length === 0;
  }

  return {
    draft,
    errors: signUpErrors(draft, touched),
    change: (field, value) => setDraft((current) => ({ ...current, [field]: value })),
    touch,
    checkAll,
  };
}
