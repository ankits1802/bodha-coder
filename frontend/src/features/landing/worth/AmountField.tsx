"use client";

import { useId } from "react";
import { cssVars } from "../motion/cssVars";
import { LANDING_TEXT } from "../strings";
import { readAmount, WORTH_BOUNDS, type WorthField } from "./estimate";
import styles from "./worth.module.css";
import { WORTH_AFFIXES, WORTH_FORMATS, type Affix } from "./worthFormat";

interface AmountFieldProps {
  field: WorthField;
  draft: string;
  value: number;
  onChange: (text: string) => void;
}

const words = LANDING_TEXT.worth;

function Unit({ affix }: { affix: Affix }) {
  return affix ? (
    <span aria-hidden="true" className="text-secondary">
      {words.units[affix]}
    </span>
  ) : null;
}

function NumberBox({ id, field, draft, onChange }: { id: string; field: WorthField; draft: string; onChange: (text: string) => void }) {
  const bounds = WORTH_BOUNDS[field];
  const affix = WORTH_AFFIXES[field];
  const invalid = readAmount(draft, bounds) === null;
  return (
    <span className={styles.number} data-invalid={invalid}>
      <Unit affix={affix.prefix} />
      <input
        id={`${id}-number`}
        type="number"
        inputMode="decimal"
        min={bounds.min}
        max={bounds.max}
        step="any"
        value={draft}
        aria-invalid={invalid || undefined}
        aria-describedby={invalid ? `${id}-error` : undefined}
        onChange={(event) => onChange(event.target.value)}
        className={styles.numberInput}
      />
      <Unit affix={affix.suffix} />
    </span>
  );
}

export function AmountField({ field, draft, value, onChange }: AmountFieldProps) {
  const id = useId();
  const bounds = WORTH_BOUNDS[field];
  const format = WORTH_FORMATS[field];
  const invalid = readAmount(draft, bounds) === null;
  const fill = ((value - bounds.min) / (bounds.max - bounds.min)) * 100;
  return (
    <div className={styles.field}>
      <div className={styles.fieldHead}>
        <label id={`${id}-label`} htmlFor={`${id}-number`} className="text-body-lg font-semibold tracking-snug">
          {words.fields[field]}
        </label>
        <NumberBox id={id} field={field} draft={draft} onChange={onChange} />
      </div>
      <input
        type="range"
        aria-labelledby={`${id}-label`}
        aria-valuetext={format(value)}
        min={bounds.min}
        max={bounds.max}
        step={bounds.step}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className={styles.range}
        style={cssVars({ "--fill": `${fill}%` })}
      />
      {invalid ? (
        <p id={`${id}-error`} className="mt-2 mb-0 text-footnote text-bad-text">
          {words.outOfRange(format(bounds.min), format(bounds.max))}
        </p>
      ) : null}
    </div>
  );
}
