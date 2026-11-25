import { HighlightedText } from "@/components/shared/HighlightedText";
import { CodeChange } from "@/components/ui/CodeChange";
import { StatusDot } from "@/components/ui/StatusDot";
import { LANDING_TEXT } from "./strings";

const words = LANDING_TEXT.product;

function WindowDots() {
  return (
    <div aria-hidden="true" className="flex h-10 items-center gap-2 border-b border-hairline px-4">
      <span className="size-2.75 rounded-full bg-separator" />
      <span className="size-2.75 rounded-full bg-separator" />
      <span className="size-2.75 rounded-full bg-separator" />
    </div>
  );
}

function Verdict() {
  return (
    <div className="px-5 pt-6 pb-4.5">
      <StatusDot tone="bad">{words.verdict}</StatusDot>
      <p className="mt-1.5 mb-0 text-title font-semibold tracking-headline">
        {words.advice}
        <span className="text-tertiary line-through">{words.struck}</span>
      </p>
    </div>
  );
}

export function ProductShot() {
  return (
    <section aria-label={words.label} className="px-6 pt-2 pb-30">
      <div className="mx-auto max-w-245 overflow-hidden rounded-feature bg-muted-panel px-4 pt-10 sm:px-10">
        <div className="overflow-hidden rounded-t-panel bg-surface shadow-product">
          <WindowDots />
          <div className="flex flex-wrap">
            <div className="min-w-0 flex-[1_1_23rem] border-r border-hairline px-7 pt-7 pb-8">
              <span className="text-caption font-semibold text-tertiary">{words.noteLabel}</span>
              <HighlightedText text={words.note} marks={[...words.marks]} className="mt-2.5 text-body leading-relaxed" />
            </div>
            <div className="min-w-0 flex-[1_1_23rem]">
              <Verdict />
              <ul className="m-0 list-none p-0">
                {words.rows.map((row) => (
                  <li key={row.before} className="flex items-center justify-between gap-3 border-t border-hairline px-5 py-3.25">
                    <CodeChange before={row.before} after={row.after} addedLabel={words.addedLabel} changedLabel={words.changedLabel} />
                    <StatusDot tone={row.tone}>{row.status}</StatusDot>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
