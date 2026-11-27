import { Button } from "@/components/ui/Button";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import type { BlindText } from "@/lib/api/types";
import { BLIND_TEXT } from "./strings";

interface BlindNoteTextProps {
  texts: BlindText[];
  pdfPending: boolean;
  onOpenPdf: () => void;
}

function heading(text: BlindText): string {
  return text.source === "document" ? BLIND_TEXT.document : BLIND_TEXT.addendum(text.revision);
}

export function BlindNoteText({ texts, pdfPending, onOpenPdf }: BlindNoteTextProps) {
  return (
    <Panel aria-label={BLIND_TEXT.noteLabel} className="min-w-0 flex-[1_1_32rem]">
      <PanelHeader
        title={BLIND_TEXT.noteLabel}
        actions={
          <Button size="sm" pending={pdfPending} onClick={onOpenPdf}>
            {BLIND_TEXT.openPdf}
          </Button>
        }
      />
      <div className="flex flex-col gap-5 px-4 pb-5">
        {texts.length === 0 ? <p className="m-0 text-secondary">{BLIND_TEXT.noText}</p> : null}
        {texts.map((text) => (
          <section key={text.revision} aria-label={heading(text)} className="flex flex-col gap-1.5">
            <h3 className="m-0 text-caption font-medium text-secondary">{heading(text)}</h3>
            <p className="m-0 text-body whitespace-pre-wrap text-label">{text.text}</p>
          </section>
        ))}
      </div>
    </Panel>
  );
}
