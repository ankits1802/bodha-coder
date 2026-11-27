"use client";

import { useState } from "react";
import { AmountField } from "./AmountField";
import {
  draftsOf,
  estimateWorth,
  readAmount,
  readDrafts,
  WORTH_BOUNDS,
  WORTH_DEFAULTS,
  WORTH_FIELDS,
  type WorthDrafts,
  type WorthField,
  type WorthInputs,
} from "./estimate";
import styles from "./worth.module.css";
import { WorthResult } from "./WorthResult";

export function Estimator() {
  const [drafts, setDrafts] = useState<WorthDrafts>(() => draftsOf(WORTH_DEFAULTS));
  const [values, setValues] = useState<WorthInputs>(WORTH_DEFAULTS);

  function change(field: WorthField, text: string): void {
    setDrafts((current) => ({ ...current, [field]: text }));
    const value = readAmount(text, WORTH_BOUNDS[field]);
    if (value !== null) setValues((current) => ({ ...current, [field]: value }));
  }

  const inputs = readDrafts(drafts);
  return (
    <div className={styles.estimator}>
      <div className={styles.fields}>
        {WORTH_FIELDS.map((field) => (
          <AmountField key={field} field={field} draft={drafts[field]} value={values[field]} onChange={(text) => change(field, text)} />
        ))}
      </div>
      <WorthResult worth={inputs ? estimateWorth(inputs) : null} inputs={inputs} />
    </div>
  );
}
