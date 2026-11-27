"use client";

import { Button } from "@/components/ui/Button";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { RemoteView } from "@/components/ui/RemoteView";
import { useRemote } from "@/hooks/useRemote";
import { getTrainingFeedback } from "@/lib/api/quality";
import { TRAINING_TEXT } from "../strings";
import { CodeComparison } from "./CodeComparison";
import { SuggestionList } from "./SuggestionList";

const REMOTE_TEXT = { loading: TRAINING_TEXT.loading, empty: TRAINING_TEXT.noSuggestions, retry: TRAINING_TEXT.retry };

export function FeedbackView({ itemId, onNext }: { itemId: string; onNext: () => void }) {
  const feedback = useRemote(`training-feedback:${itemId}`, () => getTrainingFeedback(itemId));
  return (
    <RemoteView state={feedback.state} text={REMOTE_TEXT} onRetry={feedback.reload}>
      {(data) => (
        <>
          <Panel>
            <PanelHeader
              title={TRAINING_TEXT.feedbackTitle}
              actions={
                <Button size="sm" variant="primary" onClick={onNext} autoFocus>
                  {TRAINING_TEXT.next}
                </Button>
              }
            />
            <CodeComparison feedback={data} />
          </Panel>
          <Panel>
            <PanelHeader title={TRAINING_TEXT.suggestionsTitle} />
            <SuggestionList suggestions={data.suggestions} />
          </Panel>
        </>
      )}
    </RemoteView>
  );
}
