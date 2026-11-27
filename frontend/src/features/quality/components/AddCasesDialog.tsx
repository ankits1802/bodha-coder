"use client";

import { CodeList } from "@/components/shared/CodeList";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { RemoteView } from "@/components/ui/RemoteView";
import { Table, Td, Th, Tr } from "@/components/ui/Table";
import { useAction } from "@/hooks/useAction";
import { useRemote } from "@/hooks/useRemote";
import { addEvalCase, getEvalCandidates } from "@/lib/api/quality";
import { formatCalendarDay } from "@/lib/format";
import { QUALITY_TEXT } from "../strings";

const REMOTE_TEXT = { loading: QUALITY_TEXT.loading, empty: QUALITY_TEXT.noCandidates, retry: QUALITY_TEXT.retry };

interface AddCasesDialogProps {
  onClose: () => void;
  onAdded: () => void;
}

export function AddCasesDialog({ onClose, onAdded }: AddCasesDialogProps) {
  const candidates = useRemote("quality-eval-candidates", getEvalCandidates);
  const add = useAction(addEvalCase);
  const words = QUALITY_TEXT.caseColumns;

  async function choose(noteId: string): Promise<void> {
    const outcome = await add.run(noteId);
    if (!outcome.ok) return;
    candidates.reload();
    onAdded();
  }

  return (
    <Dialog open onClose={onClose} title={QUALITY_TEXT.addCasesTitle} size="lg" footer={<Button onClick={onClose}>{QUALITY_TEXT.close}</Button>}>
      {add.error ? <InlineAlert tone="bad">{add.error}</InlineAlert> : null}
      <RemoteView state={candidates.state} text={REMOTE_TEXT} isEmpty={(data) => data.length === 0} onRetry={candidates.reload}>
        {(data) => (
          <Table label={QUALITY_TEXT.candidatesLabel} minWidth="md">
            <thead>
              <tr>
                <Th>{words.day}</Th>
                <Th>{words.provider}</Th>
                <Th>{words.claim}</Th>
                <Th>
                  <span className="sr-only">{QUALITY_TEXT.addCase}</span>
                </Th>
              </tr>
            </thead>
            <tbody>
              {data.map((row) => (
                <Tr key={row.note_id}>
                  <Td className="tabular-nums">{formatCalendarDay(row.service_date)}</Td>
                  <Td>{row.provider_name}</Td>
                  <Td>
                    <CodeList codes={row.codes} max={6} />
                  </Td>
                  <Td className="text-right">
                    <Button size="sm" disabled={add.pending} onClick={() => void choose(row.note_id)}>
                      {QUALITY_TEXT.addCase}
                    </Button>
                  </Td>
                </Tr>
              ))}
            </tbody>
          </Table>
        )}
      </RemoteView>
    </Dialog>
  );
}
