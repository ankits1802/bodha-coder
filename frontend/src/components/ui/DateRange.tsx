import { DatePicker } from "./DatePicker";
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
}

export function DateRange({ start, end, labels, onChange, min, max, today }: DateRangeProps) {
  return (
    <>
      <Field label={labels.start}>
        {(control) => (
          <DatePicker {...control} value={start} min={min} max={end ?? max} today={today} onChange={(next) => onChange({ start: next, end })} />
        )}
      </Field>
      <Field label={labels.end}>
        {(control) => (
          <DatePicker {...control} value={end} min={start ?? min} max={max} today={today} onChange={(next) => onChange({ start, end: next })} />
        )}
      </Field>
    </>
  );
}
