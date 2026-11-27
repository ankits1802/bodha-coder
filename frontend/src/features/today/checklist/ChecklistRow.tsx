import Link from "next/link";
import type { ReactNode } from "react";
import { StepMark } from "@/components/ui/StepMark";
import { TODAY_TEXT } from "../strings";
import { STEP_LINKS, type ChecklistStep } from "./checklistModel";

interface ChecklistRowProps {
  step: ChecklistStep;
  actions: ReactNode;
  children?: ReactNode;
}

export function ChecklistRow({ step, actions, children }: ChecklistRowProps) {
  const words = TODAY_TEXT.checklist;
  return (
    <li className="flex flex-col gap-3 border-t border-hairline px-4.5 py-3">
      <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
        <span className="flex min-w-0 items-center gap-3">
          <StepMark state={step.done ? "complete" : "incomplete"} label={step.done ? words.done : words.notDone} />
          <Link
            href={STEP_LINKS[step.key]}
            className={`text-body font-medium underline-offset-2 hover:underline ${step.done ? "text-secondary" : "text-label"}`}
          >
            {words.steps[step.key]}
          </Link>
        </span>
        {step.done ? null : <span className="flex flex-wrap items-center gap-2">{actions}</span>}
      </div>
      {step.done ? null : children}
    </li>
  );
}
