"use client";

import { useState } from "react";
import { Panel } from "@/components/ui/Panel";
import type { AddendumAnswer, AddendumQuestion, SignatureView } from "@/lib/api/types";
import { AddendumPanel } from "./AddendumPanel";
import { addendumHeader, canSign, draftFor, previewLines, toAnswers, type AnswerDraft, type Drafts } from "./answers";
import { QuestionCard } from "./QuestionCard";
import { RESPOND_TEXT } from "./strings";
import { useProviderSigning, type ProviderSigning } from "./useProviderSigning";

interface AnswerFormProps {
  questions: AddendumQuestion[];
  providerName: string;
  attestation: string;
  pending: boolean;
  error: string | null;
  remembered: SignatureView | null;
  onSign: (answers: AddendumAnswer[], signing: ProviderSigning) => void;
}

export function AnswerForm({ questions, providerName, attestation, pending, error, remembered, onSign }: AnswerFormProps) {
  const [drafts, setDrafts] = useState<Drafts>({});
  const [confirmed, setConfirmed] = useState(false);
  const [today] = useState(() => new Date());
  const signing = useProviderSigning(remembered, providerName);
  const signable = canSign(questions, drafts, confirmed) && signing.ready;

  function change(key: string, draft: AnswerDraft): void {
    setDrafts((current) => ({ ...current, [key]: draft }));
  }

  function sign(): void {
    if (signable) onSign(toAnswers(questions, drafts), signing);
  }

  return (
    <div className="flex flex-col gap-4">
      <Panel aria-label={RESPOND_TEXT.questions}>
        {questions.map((question, index) => (
          <QuestionCard
            key={question.key}
            number={index + 1}
            question={question}
            draft={draftFor(drafts, question.key)}
            onChange={(draft) => change(question.key, draft)}
          />
        ))}
      </Panel>
      <AddendumPanel
        header={addendumHeader(providerName, today)}
        lines={previewLines(questions, drafts)}
        confirmed={confirmed}
        onConfirm={setConfirmed}
        signable={signable}
        pending={pending}
        error={error}
        providerName={providerName}
        attestation={attestation}
        signing={signing}
        onSign={sign}
      />
    </div>
  );
}
