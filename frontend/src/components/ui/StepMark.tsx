export type StepState = "complete" | "incomplete" | "attention";

export function StepMark({ state, label }: { state: StepState; label: string }) {
  if (state === "complete") {
    return (
      <span className="flex size-4.5 flex-none items-center justify-center rounded-full bg-ok">
        <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true">
          <path d="M2 5.2l2 2L8 2.8" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" className="text-white" />
        </svg>
        <span className="sr-only">{label}</span>
      </span>
    );
  }
  if (state === "attention") {
    return (
      <span className="flex size-4.5 flex-none items-center justify-center rounded-full bg-warn text-caption font-bold text-white">
        <span aria-hidden="true">!</span>
        <span className="sr-only">{label}</span>
      </span>
    );
  }
  return (
    <span className="m-px size-4 flex-none rounded-full shadow-option">
      <span className="sr-only">{label}</span>
    </span>
  );
}
