import { Panel } from "@/components/ui/Panel";
import { formatCalendarDay } from "@/lib/format";
import { RESPOND_TEXT } from "./strings";

interface SignedPanelProps {
  title: string;
  addendumText: string;
  serviceDate: string;
}

export function SignedPanel({ title, addendumText, serviceDate }: SignedPanelProps) {
  return (
    <Panel role="status" className="flex flex-col items-center gap-2.5 px-7 py-9 text-center">
      <span aria-hidden="true" className="flex size-14 items-center justify-center rounded-full bg-ok text-white">
        <svg width="26" height="26" viewBox="0 0 20 20">
          <path d="M4.5 10.5l3.5 3.5 7.5-8" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </span>
      <h2 className="mt-1.5 mb-0 font-sans text-title3 font-semibold tracking-headline">{title}</h2>
      <p className="m-0 text-secondary">{RESPOND_TEXT.signedFor(formatCalendarDay(serviceDate, "long"))}</p>
      <div className="mt-2 w-full rounded-field bg-chip px-4 py-3.5 text-left">
        <h3 className="m-0 mb-1 font-sans text-caption font-semibold text-tertiary">{RESPOND_TEXT.addendum}</h3>
        <p className="m-0 text-body-lg whitespace-pre-wrap">{addendumText}</p>
      </div>
    </Panel>
  );
}
