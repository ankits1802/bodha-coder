"use client";

import { useState } from "react";
import { draftFrom } from "@/components/shared/signature/signatureImage";
import { useSignatureEntry, type SignatureEntryState } from "@/components/shared/signature/useSignatureEntry";
import { draftProviderSignature } from "@/lib/api/signatures";
import type { SignatureView, SigningChoice } from "@/lib/api/types";

export interface ProviderSigning {
  remembered: SignatureView | null;
  useSaved: boolean;
  entry: SignatureEntryState;
  remember: boolean;
  ready: boolean;
  setUseSaved: (value: boolean) => void;
  setRemember: (value: boolean) => void;
  choose: (providerToken: string) => Promise<SigningChoice>;
}

export function signerName(providerName: string): string {
  return providerName.split(",")[0]?.trim() ?? "";
}

export function useProviderSigning(remembered: SignatureView | null, providerName: string): ProviderSigning {
  const entry = useSignatureEntry(signerName(providerName));
  const [wantsSaved, setUseSaved] = useState(true);
  const [remember, setRemember] = useState(false);
  const useSaved = wantsSaved && remembered !== null;

  async function choose(providerToken: string): Promise<SigningChoice> {
    if (useSaved) return { signature_id: null, remember_signature: false };
    const draft = await draftProviderSignature(providerToken, await draftFrom(entry.entry));
    return { signature_id: draft.id, remember_signature: remember };
  }

  return {
    remembered,
    useSaved,
    entry,
    remember,
    ready: useSaved || entry.ready,
    setUseSaved,
    setRemember,
    choose,
  };
}
