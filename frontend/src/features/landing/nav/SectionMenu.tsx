"use client";

import { useCallback, useEffect, useId, useRef, useState, type RefObject } from "react";
import { haptic } from "@/lib/haptics";
import { cssVars } from "../motion/cssVars";
import styles from "./nav.module.css";

interface SectionLink {
  href: string;
  label: string;
}

function useDismiss(open: boolean, close: () => void, root: RefObject<HTMLDivElement | null>): void {
  useEffect(() => {
    if (!open) return;
    const onPointer = (event: PointerEvent) => {
      if (!root.current?.contains(event.target as Node)) close();
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") close();
    };
    document.addEventListener("pointerdown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open, close, root]);
}

function SectionLinks({ links, onPick }: { links: readonly SectionLink[]; onPick: () => void }) {
  return (
    <ul className="m-0 list-none p-0">
      {links.map((link, index) => (
        <li key={link.href} className={styles.item} style={cssVars({ "--i": index })}>
          <a href={link.href} onClick={onPick} className={styles.panelLink}>
            {link.label}
          </a>
        </li>
      ))}
    </ul>
  );
}

export function SectionMenu({ label, links }: { label: string; links: readonly SectionLink[] }) {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const button = useRef<HTMLButtonElement>(null);
  const panelId = useId();
  const close = useCallback(() => {
    setOpen(false);
    button.current?.focus();
  }, []);
  useDismiss(open, close, root);

  function toggle(): void {
    haptic("select");
    setOpen((current) => !current);
  }

  return (
    <div ref={root} className="flex lg:hidden">
      <button
        ref={button}
        type="button"
        aria-label={label}
        aria-expanded={open}
        aria-controls={panelId}
        onClick={toggle}
        className={styles.menuButton}
      >
        <span aria-hidden="true" className={styles.bars} />
      </button>
      <div id={panelId} hidden={!open} className={styles.panel}>
        <SectionLinks links={links} onPick={() => setOpen(false)} />
      </div>
    </div>
  );
}
