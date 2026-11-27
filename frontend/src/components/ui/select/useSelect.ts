"use client";

import { useEffect, useId, useRef, useState, type KeyboardEvent } from "react";
import { useFloating } from "../useFloating";
import { TYPEAHEAD_MS, isPrintable, navigatedOption, opensList } from "./selectKeys";
import { SEARCH_AFTER, allIndexes, edgeOption, matchingIndexes, typeaheadOption, type SelectOption } from "./selectModel";

const OPTION_HEIGHT = 34;
const SEARCH_HEIGHT = 47;
const LIST_PADDING = 8;
const MAX_HEIGHT = 320;

function keepInView(list: HTMLElement, item: HTMLElement): void {
  if (item.offsetTop < list.scrollTop) list.scrollTop = item.offsetTop;
  else if (item.offsetTop + item.offsetHeight > list.scrollTop + list.clientHeight) {
    list.scrollTop = item.offsetTop + item.offsetHeight - list.clientHeight;
  }
}

export function useSelect<V extends string>(options: readonly SelectOption<V>[], value: V, onChange: (value: V) => void) {
  const baseId = useId();
  const trigger = useRef<HTMLButtonElement>(null);
  const panel = useRef<HTMLDivElement>(null);
  const search = useRef<HTMLInputElement>(null);
  const typed = useRef({ text: "", at: Number.NEGATIVE_INFINITY });
  const float = useFloating(trigger, panel);
  const [active, setActive] = useState(-1);
  const [query, setQuery] = useState("");
  const open = float.style !== null;
  const searchable = options.length > SEARCH_AFTER;
  const shown = searchable ? matchingIndexes(options, query) : allIndexes(options);
  const selected = options.findIndex((option) => option.value === value);
  const optionId = (index: number) => `${baseId}-option-${index}`;

  useEffect(() => {
    if (open) (searchable ? search : trigger).current?.focus();
  }, [open, searchable]);

  useEffect(() => {
    const list = panel.current?.querySelector<HTMLElement>("[role=listbox]");
    const item = active >= 0 ? document.getElementById(`${baseId}-option-${active}`) : null;
    if (open && list && item) keepInView(list, item);
  }, [open, active, baseId]);

  function show(target: number, text = ""): void {
    setQuery(text);
    setActive(target);
    float.show(Math.min(MAX_HEIGHT, (searchable ? SEARCH_HEIGHT : 0) + Math.max(options.length, 1) * OPTION_HEIGHT + LIST_PADDING));
  }

  function hide(focus: boolean): void {
    float.hide();
    if (focus) trigger.current?.focus();
  }

  function choose(index: number): void {
    const option = options[index];
    hide(true);
    if (option && !option.disabled && option.value !== value) onChange(option.value);
  }

  function startAt(key = ""): number {
    if (key === "Home" || key === "End") return edgeOption(options, allIndexes(options), key === "Home" ? "first" : "last");
    return selected >= 0 && !options[selected]?.disabled ? selected : edgeOption(options, allIndexes(options), "first");
  }

  function typeahead(event: KeyboardEvent, from: number): number {
    const fresh = event.timeStamp - typed.current.at > TYPEAHEAD_MS;
    const text = (fresh ? "" : typed.current.text) + event.key;
    typed.current = { text, at: event.timeStamp };
    return typeaheadOption(options, shown, from, text);
  }

  function onClosedKey(event: KeyboardEvent<HTMLButtonElement>): void {
    if (opensList(event)) {
      event.preventDefault();
      show(startAt(event.key));
      return;
    }
    if (!isPrintable(event)) return;
    event.preventDefault();
    if (searchable) {
      show(edgeOption(options, matchingIndexes(options, event.key), "first"), event.key);
      return;
    }
    const found = typeahead(event, selected);
    show(found >= 0 ? found : startAt());
  }

  function commitKey(event: KeyboardEvent): boolean {
    if (event.key === "Escape") {
      event.preventDefault();
      event.stopPropagation();
      hide(true);
      return true;
    }
    if (event.key === "Tab") choose(active);
    else if (event.key === "Enter" || (event.altKey && event.key === "ArrowUp")) {
      event.preventDefault();
      choose(active);
    } else return false;
    return true;
  }

  function onOpenKey(event: KeyboardEvent<HTMLButtonElement>): void {
    const typingAhead = typed.current.text !== "" && event.timeStamp - typed.current.at <= TYPEAHEAD_MS;
    if (commitKey(event)) return;
    if (event.key === " " && !typingAhead) {
      event.preventDefault();
      choose(active);
      return;
    }
    const target = navigatedOption(options, shown, active, event.key);
    if (target === null && !isPrintable(event)) return;
    event.preventDefault();
    const next = target ?? typeahead(event, active);
    if (next >= 0) setActive(next);
  }

  function onSearchKey(event: KeyboardEvent<HTMLInputElement>): void {
    if (commitKey(event) || event.key === "Home" || event.key === "End") return;
    const target = navigatedOption(options, shown, active, event.key);
    if (target === null) return;
    event.preventDefault();
    setActive(target);
  }

  const view = {
    open,
    searchable,
    shown,
    active,
    query,
    style: float.style ? { ...float.style, maxHeight: Math.min(float.style.maxHeight, MAX_HEIGHT) } : null,
    width: float.width,
    listId: `${baseId}-list`,
    optionId,
    choose,
    toggle: () => (open ? hide(false) : show(startAt())),
    onTriggerKey: open ? onOpenKey : onClosedKey,
    onSearchKey,
    onSearch: (text: string) => {
      setQuery(text);
      setActive(edgeOption(options, matchingIndexes(options, text), "first"));
    },
    onHover: (index: number) => {
      if (index !== active) setActive(index);
    },
  };
  return { triggerRef: trigger, panelRef: panel, searchRef: search, view };
}

export type SelectView<V extends string> = ReturnType<typeof useSelect<V>>["view"];
