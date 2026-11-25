"use client";

import { useState } from "react";
import { CodeForm } from "./CodeForm";
import { RecoveryCodeForm } from "./RecoveryCodeForm";
import { SIGN_IN_TEXT } from "./strings";

export interface Submission {
  pending: boolean;
  error: string | null;
  onSubmit: (value: string) => void;
}

interface MfaVerifyProps {
  email: string | null;
  code: Submission;
  recovery: Submission;
  onCancel: () => void;
}

export function MfaVerify({ email, code, recovery, onCancel }: MfaVerifyProps) {
  const [usingRecovery, setUsingRecovery] = useState(false);
  return (
    <div className="flex flex-col gap-5.5">
      <div className="flex flex-col gap-1 text-center">
        <h2 className="m-0 font-sans text-headline font-semibold tracking-snug">{SIGN_IN_TEXT.verifyTitle}</h2>
        {usingRecovery ? null : (
          <p className="m-0 text-body text-secondary">
            {email ? SIGN_IN_TEXT.verifyPrompt(email) : SIGN_IN_TEXT.verifyPromptPlain}
          </p>
        )}
      </div>
      {usingRecovery ? (
        <RecoveryCodeForm
          {...recovery}
          onCancel={onCancel}
          alternative={{ label: SIGN_IN_TEXT.useSixDigits, onSelect: () => setUsingRecovery(false) }}
        />
      ) : (
        <CodeForm
          {...code}
          onCancel={onCancel}
          alternative={{ label: SIGN_IN_TEXT.useRecoveryCode, onSelect: () => setUsingRecovery(true) }}
        />
      )}
    </div>
  );
}
