"use client";

import Image from "next/image";
import type { MfaEnrolment } from "@/lib/api/types";
import { CodeForm } from "./CodeForm";
import { SIGN_IN_TEXT } from "./strings";

interface MfaSetupProps {
  enrolment: MfaEnrolment;
  pending: boolean;
  error: string | null;
  onSubmit: (code: string) => void;
  onCancel: () => void;
}

const QR_SIZE = 176;

function groupedSecret(secret: string): string {
  return secret.match(/.{1,4}/g)?.join(" ") ?? secret;
}

export function MfaSetup({ enrolment, pending, error, onSubmit, onCancel }: MfaSetupProps) {
  return (
    <div className="flex flex-col gap-5.5">
      <div className="flex flex-col gap-1 text-center">
        <h2 className="m-0 font-sans text-headline font-semibold tracking-snug">{SIGN_IN_TEXT.setupTitle}</h2>
        <p className="m-0 text-body text-secondary">{SIGN_IN_TEXT.setupPrompt}</p>
      </div>
      <div className="flex flex-col items-center gap-3">
        <Image
          src={enrolment.qr_image}
          alt={SIGN_IN_TEXT.qrAlt}
          width={QR_SIZE}
          height={QR_SIZE}
          unoptimized
          className="rounded-field bg-paper shadow-field"
        />
        <div className="flex flex-col items-center gap-0.5">
          <span className="text-caption text-tertiary">{SIGN_IN_TEXT.secretLabel}</span>
          <span className="text-callout font-semibold tracking-normal break-all tabular-nums select-all">
            {groupedSecret(enrolment.secret)}
          </span>
        </div>
      </div>
      <CodeForm pending={pending} error={error} onSubmit={onSubmit} onCancel={onCancel} />
    </div>
  );
}
