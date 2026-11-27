"use client";

import { useId, useState } from "react";
import { haptic } from "@/lib/haptics";
import styles from "./faq.module.css";

export interface FaqItem {
  question: string;
  answer: string;
}

interface FaqEntryProps {
  id: string;
  item: FaqItem;
  expanded: boolean;
  onToggle: () => void;
}

function FaqEntry({ id, item, expanded, onToggle }: FaqEntryProps) {
  return (
    <div className={styles.item}>
      <h3 className="m-0">
        <button id={`${id}-question`} type="button" aria-expanded={expanded} aria-controls={`${id}-answer`} onClick={onToggle} className={styles.question}>
          <span>{item.question}</span>
          <span aria-hidden="true" className={styles.plus} />
        </button>
      </h3>
      <div id={`${id}-answer`} hidden={!expanded} className={styles.answer}>
        <p className="m-0">{item.answer}</p>
      </div>
    </div>
  );
}

export function FaqList({ items }: { items: readonly FaqItem[] }) {
  const [open, setOpen] = useState<ReadonlySet<number>>(() => new Set());
  const base = useId();

  function toggle(index: number): void {
    haptic("select");
    setOpen((current) => {
      const next = new Set(current);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  }

  return (
    <div className={styles.list}>
      {items.map((item, index) => (
        <FaqEntry key={item.question} id={`${base}-${index}`} item={item} expanded={open.has(index)} onToggle={() => toggle(index)} />
      ))}
    </div>
  );
}
