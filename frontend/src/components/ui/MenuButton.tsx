"use client";

import { useEffect, useId, useRef, type KeyboardEvent } from "react";
import { useFloating } from "./useFloating";

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

const STEP: Record<string, number> = { ArrowDown: 1, ArrowUp: -1 };
const ITEM_HEIGHT = 34;
const PADDING = 8;

export function MenuButton({ label, items, disabled = false }: MenuButtonProps) {
  const menuId = useId();
  const menu = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const entries = useRef<(HTMLButtonElement | null)[]>([]);
  const float = useFloating(trigger, menu, "end");
  const open = float.style !== null;

  useEffect(() => {
    if (open) entries.current.find((entry) => entry && !entry.disabled)?.focus();
  }, [open]);

  function toggle(): void {
    if (open) float.hide();
    else float.show(items.length * ITEM_HEIGHT + PADDING);
  }

  function close(): void {
    float.hide();
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
      {float.style ? (
        <div
          ref={menu}
          id={menuId}
          role="menu"
          aria-label={label}
          onKeyDown={onMenuKey}
          style={float.style}
          className="fixed z-30 flex min-w-48 flex-col overflow-y-auto rounded-field bg-surface py-1 shadow-float"
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
              className={`h-8.5 flex-none cursor-pointer px-3.5 text-left text-body whitespace-nowrap hover:bg-row-hover focus:bg-row-selected focus:outline-none disabled:cursor-not-allowed disabled:text-tertiary ${item.tone === "danger" ? "text-bad-text" : "text-label"}`}
            >
              {item.label}
            </button>
          ))}
        </div>
      ) : null}
    </>
  );
}
