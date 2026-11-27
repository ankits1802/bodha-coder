"use client";

import { useAction, type Action } from "@/hooks/useAction";
import { useRemote, type Remote } from "@/hooks/useRemote";
import { getBlindDocument, getBlindStep, submitBlindAnswer } from "@/lib/api/quality";
import type { BlindAnswer, BlindStep, BlindSubmitted } from "@/lib/api/types";
import { openDocument } from "@/lib/openDocument";

export interface BlindSession {
  step: Remote<BlindStep>;
  submit: Action<[string, BlindAnswer], BlindSubmitted>;
  pdf: Action<[string], void>;
}

export function useBlindSession(sampleId: string): BlindSession {
  const step = useRemote(`blind:${sampleId}`, () => getBlindStep(sampleId));
  const submit = useAction((itemId: string, answer: BlindAnswer) => submitBlindAnswer(itemId, answer));
  const pdf = useAction((itemId: string) => openDocument(() => getBlindDocument(itemId)));
  return { step, submit, pdf };
}
