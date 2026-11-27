import { DatePicker, type DatePickerVariant } from "./DatePicker";
import { Field } from "./Field";

export interface DateRangeValue {
  start: string | null;
  end: string | null;
}

interface DateRangeProps extends DateRangeValue {
  labels: { start: string; end: string };
  onChange: (range: DateRangeValue) => void;
  min?: string;
  max?: string;
  today?: string;
  variant?: DatePickerVariant;
}

export function DateRange({ start, end, labels, onChange, min, max, today, variant = "field" }: DateRangeProps) {
  const startBounds = {
    value: start,
    min,
    max: end ?? max,
    today,
    onChange: (next: string | null) => onChange({ start: next, end }),
  };
  const endBounds = {
    value: end,
    min: start ?? min,
    max,
    today,
    onChange: (next: string | null) => onChange({ start, end: next }),
  };
  if (variant === "filter") {
    return (
      <>
        <DatePicker variant="filter" label={labels.start} {...startBounds} />
        <DatePicker variant="filter" label={labels.end} {...endBounds} />
      </>
    );
  }
  return (
    <>
      <Field label={labels.start}>{(control) => <DatePicker {...control} {...startBounds} />}</Field>
      <Field label={labels.end}>{(control) => <DatePicker {...control} {...endBounds} />}</Field>
    </>
  );
}
