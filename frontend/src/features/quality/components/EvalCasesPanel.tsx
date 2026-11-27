"use client";

import { useState } from "react";
import { CodeList } from "@/components/shared/CodeList";
import { Button } from "@/components/ui/Button";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { RemoteView } from "@/components/ui/RemoteView";
import { Table, Td, Th, Tr } from "@/components/ui/Table";
import { useAction } from "@/hooks/useAction";
import { useRemote } from "@/hooks/useRemote";
import { getEvalCases, removeEvalCase } from "@/lib/api/quality";
import { FORMAT_WORDS, formatCalendarDay } from "@/lib/format";
import { QUALITY_TEXT } from "../strings";
import { AddCasesDialog } from "./AddCasesDialog";

const REMOTE_TEXT = { loading: QUALITY_TEXT.loading, empty: QUALITY_TEXT.noCases, retry: QUALITY_TEXT.retry };

interface EvalCasesPanelProps {
  editable: boolean;
  onChanged: () => void;
}

export function EvalCasesPanel({ editable, onChanged }: EvalCasesPanelProps) {
  const cases = useRemote("quality-eval-cases", getEvalCases);
  const remove = useAction(removeEvalCase);
  const [adding, setAdding] = useState(false);
  const words = QUALITY_TEXT.caseColumns;
  const changed = () => {
    cases.reload();
    onChanged();
  };

  async function drop(noteId: string): Promise<void> {
    if ((await remove.run(noteId)).ok) changed();
  }

  const actions = editable ? (
    <Button size="sm" onClick={() => setAdding(true)}>
      {QUALITY_TEXT.addCases}
    </Button>
  ) : null;
  return (
    <Panel>
      <PanelHeader title={QUALITY_TEXT.casesTitle} actions={actions} />
      {remove.error ? <InlineAlert tone="bad">{remove.error}</InlineAlert> : null}
      <RemoteView state={cases.state} text={REMOTE_TEXT} isEmpty={(data) => data.length === 0} onRetry={cases.reload}>
        {(data) => (
          <Table label={QUALITY_TEXT.casesLabel} minWidth="lg">
            <thead>
              <tr>
                <Th>{words.day}</Th>
                <Th>{words.provider}</Th>
                <Th>{words.em}</Th>
                <Th>{words.level}</Th>
                <Th>{words.icd}</Th>
                <Th>{words.modifiers}</Th>
                {editable ? (
                  <Th>
                    <span className="sr-only">{QUALITY_TEXT.removeCase}</span>
                  </Th>
                ) : null}
              </tr>
            </thead>
            <tbody>
              {data.map((row) => (
                <Tr key={row.note_id}>
                  <Td className="tabular-nums">{formatCalendarDay(row.service_date)}</Td>
                  <Td>{row.provider_name}</Td>
                  <Td>
                    <CodeList codes={row.em ? [row.em] : []} />
                  </Td>
                  <Td>{row.level ?? FORMAT_WORDS.empty}</Td>
                  <Td>
                    <CodeList codes={row.icd} max={5} />
                  </Td>
                  <Td>
                    <CodeList codes={row.modifiers} />
                  </Td>
                  {editable ? (
                    <Td className="text-right">
                      <Button size="sm" variant="danger" disabled={remove.pending} onClick={() => void drop(row.note_id)}>
                        {QUALITY_TEXT.removeCase}
                      </Button>
                    </Td>
                  ) : null}
                </Tr>
              ))}
            </tbody>
          </Table>
        )}
      </RemoteView>
      {adding ? <AddCasesDialog onClose={() => setAdding(false)} onAdded={changed} /> : null}
    </Panel>
  );
}
