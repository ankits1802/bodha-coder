import { StatusDot, type StatusTone } from "@/components/ui/StatusDot";
import { formatMoney } from "@/lib/format";
import { LANDING_TEXT } from "../strings";
import type { Worth, WorthInputs } from "./estimate";
import styles from "./worth.module.css";
import { WORTH_FORMATS } from "./worthFormat";

const words = LANDING_TEXT.worth;

type Side = "low" | "high";

interface SideView {
  tone: StatusTone;
  words: { status: string; label: string };
  month: (worth: Worth) => number;
  year: (worth: Worth) => number;
  percent: (inputs: WorthInputs) => number;
}

const SIDES: Record<Side, SideView> = {
  low: {
    tone: "low",
    words: words.low,
    month: (worth) => worth.recovered,
    year: (worth) => worth.recoveredYear,
    percent: (inputs) => inputs.lowPercent,
  },
  high: {
    tone: "bad",
    words: words.high,
    month: (worth) => worth.exposure,
    year: (worth) => worth.exposureYear,
    percent: (inputs) => inputs.highPercent,
  },
};

function Formula({ inputs, percent }: { inputs: WorthInputs; percent: number }) {
  const parts = [WORTH_FORMATS.visits(inputs.visits), WORTH_FORMATS.lowPercent(percent), WORTH_FORMATS.difference(inputs.difference)];
  return (
    <p className={styles.formula}>
      {parts.map((part, index) => (
        <span key={`${part}-${index}`}>
          {index > 0 ? <span aria-hidden="true">{` ${words.times} `}</span> : null}
          {part}
        </span>
      ))}
    </p>
  );
}

function Result({ side, worth, inputs }: { side: Side; worth: Worth | null; inputs: WorthInputs | null }) {
  const view = SIDES[side];
  return (
    <div className={styles.result}>
      <StatusDot tone={view.tone}>{view.words.status}</StatusDot>
      <p className="mt-3 mb-0 text-subhead text-secondary">{view.words.label}</p>
      <output className={styles.amount}>
        {formatMoney(worth ? view.month(worth) : null)} <span className={styles.per}>{words.perMonth}</span>
      </output>
      <p className="mt-1 mb-0 text-body text-label-soft tabular-nums">{`${formatMoney(worth ? view.year(worth) : null)} ${words.perYear}`}</p>
      {inputs ? <Formula inputs={inputs} percent={view.percent(inputs)} /> : null}
    </div>
  );
}

export function WorthResult({ worth, inputs }: { worth: Worth | null; inputs: WorthInputs | null }) {
  return (
    <div className={styles.results}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-footnote font-semibold text-secondary">{words.estimate}</span>
        <span className={styles.note}>{words.note}</span>
      </div>
      <Result side="low" worth={worth} inputs={inputs} />
      <Result side="high" worth={worth} inputs={inputs} />
    </div>
  );
}
