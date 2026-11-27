import type { NoteChangeRecord, NoteStatus } from "@/lib/api/types";
import { REVIEW_TEXT } from "../strings";
import { HistoryEntry, HistoryList, joinMeta } from "./HistoryEntry";

const words = REVIEW_TEXT.history;

function isNoteStatus(value: string): value is NoteStatus {
  return value in words.noteStatus;
}

export function changeValue(change: NoteChangeRecord, value: string | null): string {
  if (value === null) return words.notSet;
  return change.field === "status" && isNoteStatus(value) ? words.noteStatus[value] : value;
}

export function HistoryChanges({ changes }: { changes: NoteChangeRecord[] }) {
  return (
    <HistoryList>
      {changes.map((change, index) => (
        <HistoryEntry
          key={`${change.field}-${change.at}-${index}`}
          at={change.at}
          title={
            <>
              <span className="font-medium">{words.field[change.field]}</span>
              <span>{words.change(changeValue(change, change.old), changeValue(change, change.new))}</span>
            </>
          }
          meta={joinMeta([change.reason, words.by(change.by ?? words.system)])}
        />
      ))}
    </HistoryList>
  );
}
