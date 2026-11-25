import { HighlightedText } from "@/components/shared/HighlightedText";
import { Panel } from "@/components/ui/Panel";
import type { Mark } from "@/lib/highlight";
import type { ProviderRequest } from "@/lib/api/types";
import { RESPOND_TEXT } from "./strings";

interface NotePanelProps {
  request: ProviderRequest;
}

const SECTION_LABEL = "m-0 mb-1 font-sans text-caption font-semibold text-tertiary";

function contextMarks(request: ProviderRequest): Mark[] {
  return request.questions.flatMap((question) => question.context.map((quote) => ({ quote, tone: "warn" as const })));
}

export function NotePanel({ request }: NotePanelProps) {
  const marks = contextMarks(request);
  const texts = [...request.texts].sort((a, b) => a.revision - b.revision);
  return (
    <Panel aria-label={RESPOND_TEXT.yourNote} className="min-w-0 flex-[1_1_35rem]">
      <div className="border-b border-hairline px-5 py-3.5">
        <h2 className="m-0 font-sans text-body-lg font-semibold">{RESPOND_TEXT.yourNote}</h2>
      </div>
      <article className="flex flex-col gap-5 px-6.5 pt-5.5 pb-6.5 text-body-lg leading-relaxed">
        {texts.map((text) =>
          text.source === "document" ? (
            <section key={text.revision} aria-label={RESPOND_TEXT.noteText}>
              <HighlightedText text={text.text} marks={marks} />
            </section>
          ) : (
            <section key={text.revision} className="rounded-field bg-chip px-4 py-3.5">
              <h3 className={SECTION_LABEL}>{RESPOND_TEXT.addendum}</h3>
              <p className="m-0 whitespace-pre-wrap">{text.text}</p>
            </section>
          ),
        )}
      </article>
    </Panel>
  );
}
