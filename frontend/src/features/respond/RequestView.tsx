"use client";

import { useState } from "react";
import { EmptyState } from "@/components/ui/EmptyState";
import { Panel } from "@/components/ui/Panel";
import { RemoteView } from "@/components/ui/RemoteView";
import { useAction } from "@/hooks/useAction";
import { useRemote } from "@/hooks/useRemote";
import { getProviderDocument, getProviderRequest, submitAnswers } from "@/lib/api/respond";
import type { AddendumAnswer, ProviderRequest, RespondResult } from "@/lib/api/types";
import { openDocument } from "@/lib/openDocument";
import { AnswerForm } from "./AnswerForm";
import { NotePanel } from "./NotePanel";
import { watchExpiry } from "./providerSession";
import { RequestHeader } from "./RequestHeader";
import { SignedPanel } from "./SignedPanel";
import { RESPOND_TEXT } from "./strings";
import { TopBar } from "./TopBar";

interface RequestViewProps {
  providerToken: string;
  onExpired: () => void;
}

interface SideProps {
  request: ProviderRequest;
  result: RespondResult | null;
  pending: boolean;
  error: string | null;
  onSign: (answers: AddendumAnswer[]) => void;
}

const REMOTE_TEXT = { loading: RESPOND_TEXT.loading, empty: "", retry: RESPOND_TEXT.retry };

function Side({ request, result, pending, error, onSign }: SideProps) {
  if (result) {
    return (
      <SignedPanel
        title={RESPOND_TEXT.signedTitle}
        addendumText={result.addendum_text}
        serviceDate={request.service_date}
        answeredAt={null}
      />
    );
  }
  if (request.status === "answered" && request.addendum_text) {
    return (
      <SignedPanel
        title={RESPOND_TEXT.answeredTitle}
        addendumText={request.addendum_text}
        serviceDate={request.service_date}
        answeredAt={request.answered_at}
      />
    );
  }
  if (request.status !== "sent") {
    return (
      <Panel>
        <EmptyState title={RESPOND_TEXT.closed} />
      </Panel>
    );
  }
  return (
    <AnswerForm questions={request.questions} providerName={request.provider_name} pending={pending} error={error} onSign={onSign} />
  );
}

export function RequestView({ providerToken, onExpired }: RequestViewProps) {
  const remote = useRemote(`respond:${providerToken}`, () => watchExpiry(getProviderRequest(providerToken), onExpired));
  const sign = useAction((answers: AddendumAnswer[]) => watchExpiry(submitAnswers(providerToken, answers), onExpired));
  const pdf = useAction(() => openDocument(() => watchExpiry(getProviderDocument(providerToken), onExpired)));
  const [result, setResult] = useState<RespondResult | null>(null);
  const request = remote.state.status === "success" ? remote.state.data : null;

  async function submit(answers: AddendumAnswer[]): Promise<void> {
    const outcome = await sign.run(answers);
    if (outcome.ok) setResult(outcome.value);
  }

  return (
    <div className="flex min-h-screen flex-col bg-page">
      <TopBar practiceName={request?.practice_name} providerName={request?.provider_name} />
      <main className="mx-auto flex w-full max-w-310 flex-1 flex-col gap-6 px-4 pt-9 pb-12 sm:px-8">
        <RemoteView state={remote.state} text={REMOTE_TEXT} onRetry={remote.reload}>
          {(data) => (
            <>
              <RequestHeader request={data} pdfPending={pdf.pending} pdfError={pdf.error} onOpenPdf={() => void pdf.run()} />
              <div className="flex flex-wrap items-start gap-6">
                <NotePanel request={data} />
                <div className="flex min-w-0 flex-[1_1_26rem] flex-col gap-4">
                  <Side
                    request={data}
                    result={result}
                    pending={sign.pending}
                    error={sign.error}
                    onSign={(answers) => void submit(answers)}
                  />
                </div>
              </div>
            </>
          )}
        </RemoteView>
      </main>
    </div>
  );
}
