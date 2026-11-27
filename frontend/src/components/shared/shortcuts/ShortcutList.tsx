"use client";

import { Fragment, useSyncExternalStore } from "react";
import type { Role } from "@/lib/api/types";
import { SHARED_TEXT } from "../strings";
import { comboKeys, shortcutsIn, type KeyCombo, type ShortcutScope } from "./registry";

interface ShortcutListProps {
  scopes: readonly ShortcutScope[];
  role: Role;
}

const APPLE_PLATFORM = /Mac|iPhone|iPad/;

function noChange(): () => void {
  return () => undefined;
}

function useIsMac(): boolean {
  return useSyncExternalStore(
    noChange,
    () => APPLE_PLATFORM.test(navigator.userAgent),
    () => false,
  );
}

function Combo({ combo, mac }: { combo: KeyCombo; mac: boolean }) {
  return (
    <span className="inline-flex items-center gap-1">
      {comboKeys(combo, mac).map((key) => (
        <kbd
          key={key}
          className="inline-flex h-6 min-w-6 items-center justify-center rounded-control bg-chip px-1.5 font-sans text-caption font-semibold text-label"
        >
          {key}
        </kbd>
      ))}
    </span>
  );
}

export function ShortcutList({ scopes, role }: ShortcutListProps) {
  const mac = useIsMac();
  const words = SHARED_TEXT.shortcuts;
  const groups = scopes.map((scope) => ({ scope, entries: shortcutsIn(scope, role) })).filter((group) => group.entries.length > 0);
  return (
    <div className="flex flex-col gap-5">
      {groups.map(({ scope, entries }) => (
        <section key={scope} aria-label={words.scopes[scope]} className="flex flex-col gap-1">
          <h3 className="m-0 font-sans text-caption font-semibold text-tertiary">{words.scopes[scope]}</h3>
          <dl className="m-0 flex flex-col">
            {entries.map((entry) => (
              <div key={entry.id} className="flex items-center justify-between gap-4 border-b border-hairline py-2 last:border-b-0">
                <dt className="text-body">{words.labels[entry.id]}</dt>
                <dd className="m-0 flex flex-wrap items-center justify-end gap-1.5 text-caption text-secondary">
                  {entry.combos.map((combo, index) => (
                    <Fragment key={`${combo.key}-${combo.withModifier ? "mod" : "plain"}`}>
                      {index > 0 ? <span>{words.or}</span> : null}
                      <Combo combo={combo} mac={mac} />
                    </Fragment>
                  ))}
                </dd>
              </div>
            ))}
          </dl>
        </section>
      ))}
    </div>
  );
}
