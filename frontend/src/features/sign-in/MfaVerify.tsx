"use client";

import { CodeForm } from "./CodeForm";
import { SIGN_IN_TEXT } from "./strings";

interface MfaVerifyProps {
  email: string;
  pending: boolean;
  error: string | null;
  onSubmit: (code: string) => void;
  onCancel: () => void;
}

export function MfaVerify({ email, pending, error, onSubmit, onCancel }: MfaVerifyProps) {
  return (
    <div className="flex flex-col gap-5.5">
      <div className="flex flex-col gap-1 text-center">
        <h2 className="m-0 font-sans text-headline font-semibold tracking-snug">{SIGN_IN_TEXT.verifyTitle}</h2>
        <p className="m-0 text-body text-secondary">{SIGN_IN_TEXT.verifyPrompt(email)}</p>
      </div>
      <CodeForm pending={pending} error={error} onSubmit={onSubmit} onCancel={onCancel} />
    </div>
  );
}
