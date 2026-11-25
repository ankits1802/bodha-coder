"use client";

import { useEffect, useId, useRef, useState, type KeyboardEvent } from "react";

export interface MenuItem {
  key: string;
  label: string;
  onSelect: () => void;
  tone?: "default" | "danger";
  disabled?: boolean;
}

interface MenuButtonProps {
  label: string;
  items: MenuItem[];
  disabled?: boolean;
}

interface Placement {
  top: number;
  right: number;
}

const STEP: Record<string, number> = { ArrowDown: 1, ArrowUp: -1 };
const ITEM_HEIGHT = 34;
const GAP = 4;

function placementFor(trigger: HTMLElement, count: number): Placement {
  const rect = trigger.getBoundingClientRect();
  const height = count * ITEM_HEIGHT + 2 * GAP;
  const below = rect.bottom + GAP;
  const top = below + height > window.innerHeight ? Math.max(GAP, rect.top - height - GAP) : below;
  return { top, right: Math.max(GAP, window.innerWidth - rect.right) };
}

export function MenuButton({ label, items, disabled = false }: MenuButtonProps) {
  const [placement, setPlacement] = useState<Placement | null>(null);
  const open = placement !== null;
  const menuId = useId();
  const menu = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const entries = useRef<(HTMLButtonElement | null)[]>([]);

  useEffect(() => {
    if (!open) return;
    entries.current.find((entry) => entry && !entry.disabled)?.focus();
    const onPointer = (event: MouseEvent) => {
      const target = event.target as Node;
      if (!menu.current?.contains(target) && !trigger.current?.contains(target)) setPlacement(null);
    };
    const dismiss = () => setPlacement(null);
    document.addEventListener("mousedown", onPointer);
    window.addEventListener("resize", dismiss);
    window.addEventListener("scroll", dismiss, true);
    return () => {
      document.removeEventListener("mousedown", onPointer);
      window.removeEventListener("resize", dismiss);
      window.removeEventListener("scroll", dismiss, true);
    };
  }, [open]);

  function toggle(): void {
    if (open || !trigger.current) setPlacement(null);
    else setPlacement(placementFor(trigger.current, items.length));
  }

  function close(): void {
    setPlacement(null);
    trigger.current?.focus();
  }

  function onMenuKey(event: KeyboardEvent<HTMLDivElement>): void {
    if (event.key === "Escape" || event.key === "Tab") {
      event.preventDefault();
      close();
      return;
    }
    const step = STEP[event.key];
    if (step === undefined) return;
    event.preventDefault();
    const usable = entries.current.filter((entry): entry is HTMLButtonElement => entry !== null && !entry.disabled);
    const at = usable.indexOf(document.activeElement as HTMLButtonElement);
    usable[(at + step + usable.length) % usable.length]?.focus();
  }

  return (
    <>
      <button
        ref={trigger}
        type="button"
        aria-label={label}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? menuId : undefined}
        disabled={disabled || items.length === 0}
        onClick={toggle}
        className="size-7.5 cursor-pointer rounded-full text-body-lg leading-none text-secondary hover:bg-fill-plain-hover disabled:cursor-not-allowed disabled:opacity-40"
      >
        <span aria-hidden="true">···</span>
      </button>
      {placement ? (
        <div
          ref={menu}
          id={menuId}
          role="menu"
          aria-label={label}
          onKeyDown={onMenuKey}
          style={{ top: placement.top, right: placement.right }}
          className="fixed z-30 flex min-w-48 flex-col rounded-field bg-surface py-1 shadow-float"
        >
          {items.map((item, index) => (
            <button
              key={item.key}
              ref={(node) => {
                entries.current[index] = node;
              }}
              type="button"
              role="menuitem"
              tabIndex={-1}
              disabled={item.disabled}
              onClick={() => {
                close();
                item.onSelect();
              }}
              className={`h-8.5 cursor-pointer px-3.5 text-left text-body whitespace-nowrap hover:bg-row-hover focus:bg-row-selected focus:outline-none disabled:cursor-not-allowed disabled:text-tertiary ${item.tone === "danger" ? "text-bad-text" : "text-label"}`}
            >
              {item.label}
            </button>
          ))}
        </div>
      ) : null}
    </>
  );
}
