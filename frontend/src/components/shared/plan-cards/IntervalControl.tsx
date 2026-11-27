"use client";

import { SegmentedControl } from "@/components/ui/SegmentedControl";
import type { BillingInterval } from "@/lib/api/types";
import { PLAN_CARD_TEXT } from "./strings";

interface IntervalControlProps {
  value: BillingInterval;
  onChange: (interval: BillingInterval) => void;
  monthsFree: number | null;
}

export function IntervalControl({ value, onChange, monthsFree }: IntervalControlProps) {
  const words = PLAN_CARD_TEXT;
  const annual = (
    <>
      {words.intervals.annual}
      {monthsFree !== null ? (
        <>
          {" "}
          <span className="font-normal text-label-soft">{words.monthsFree(monthsFree)}</span>
        </>
      ) : null}
    </>
  );
  return (
    <SegmentedControl<BillingInterval>
      label={words.intervalLabel}
      value={value}
      onChange={onChange}
      segments={[
        { value: "monthly", label: words.intervals.monthly },
        { value: "annual", label: annual },
      ]}
    />
  );
}
