import type { ReactNode } from "react";
import type { NoteDetail } from "@/lib/api/types";
import { useSession } from "@/lib/session/useSession";
import { canUse } from "@/lib/roles";
import { REVIEW_TEXT } from "../strings";
import { HistoryChanges } from "./HistoryChanges";
import { HistoryComments } from "./HistoryComments";
import { CodeRevisions, Decisions, Readings } from "./HistoryReadings";
import { AttestationHistory, ExportHistory, SnapshotHistory } from "./HistoryRecords";
import { HistoryRequests } from "./HistoryRequests";
import { HistoryReturns } from "./HistoryReturns";
import { ReviewSection } from "./ReviewSection";

const words = REVIEW_TEXT.history;

function Section({ title, count, children }: { title: string; count: number; children: ReactNode }) {
  return (
    <ReviewSection title={title}>
      {count === 0 ? <p className="m-0 text-callout text-tertiary">{words.none}</p> : children}
    </ReviewSection>
  );
}

export function HistoryContent({ detail }: { detail: NoteDetail }) {
  const { history, requests } = detail;
  const { user } = useSession();
  return (
    <>
      <Section title={words.comments} count={1}>
        <HistoryComments findings={detail.findings} />
      </Section>
      <Section title={words.analyses} count={history.analyses.length}>
        <Readings detail={detail} />
      </Section>
      <Section title={words.codeSets} count={history.code_sets.length}>
        <CodeRevisions detail={detail} />
      </Section>
      <Section title={words.decisions} count={history.decisions.length}>
        <Decisions detail={detail} />
      </Section>
      <Section title={words.changes} count={history.changes.length}>
        <HistoryChanges changes={history.changes} />
      </Section>
      <Section title={words.returns} count={history.returns.length}>
        <HistoryReturns returns={history.returns} />
      </Section>
      <Section title={words.requests} count={requests.length}>
        <HistoryRequests requests={requests} />
      </Section>
      <Section title={words.attestations} count={history.attestations.length}>
        <AttestationHistory attestations={history.attestations} />
      </Section>
      <Section title={words.snapshots} count={history.snapshots.length}>
        <SnapshotHistory snapshots={history.snapshots} />
      </Section>
      <Section title={words.exports} count={history.exports.length}>
        <ExportHistory exports={history.exports} canDownload={canUse(user?.role, "billing")} />
      </Section>
    </>
  );
}
