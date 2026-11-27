import { Panel } from "@/components/ui/Panel";
import type { BlindAnswer, BlindItem } from "@/lib/api/types";
import { BlindCodingForm } from "./BlindCodingForm";
import { BlindNoteText } from "./BlindNoteText";
import { BLIND_TEXT } from "./strings";

interface BlindCodingPanelProps {
  item: BlindItem;
  total: number;
  pending: boolean;
  error: string | null;
  pdfPending: boolean;
  onSubmit: (answer: BlindAnswer) => void;
  onOpenPdf: () => void;
}

export function BlindCodingPanel({ item, total, pending, error, pdfPending, onSubmit, onOpenPdf }: BlindCodingPanelProps) {
  return (
    <div className="flex flex-col gap-4">
      <p className="m-0 text-subhead text-secondary tabular-nums">{BLIND_TEXT.progress(item.position, total)}</p>
      <div className="flex flex-wrap items-start gap-4">
        <BlindNoteText texts={item.texts} pdfPending={pdfPending} onOpenPdf={onOpenPdf} />
        <Panel className="min-w-0 flex-[1_1_18rem] px-4 py-4">
          <BlindCodingForm key={item.id} pending={pending} error={error} onSubmit={onSubmit} />
        </Panel>
      </div>
    </div>
  );
}
