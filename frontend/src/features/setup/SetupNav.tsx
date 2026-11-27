import Link from "next/link";
import { Panel } from "@/components/ui/Panel";
import { setupSectionPath } from "@/lib/paths";
import type { PracticeSetup } from "@/lib/api/types";
import { NAV_ORDER, markerFor, type SectionMarker } from "./setupModel";
import { SETUP_TEXT, type SetupNavKey } from "./strings";

function Marker({ marker }: { marker: SectionMarker }) {
  if (marker === "none") return <span aria-hidden="true" className="size-4.5 flex-none" />;
  const text = SETUP_TEXT.marker[marker];
  if (marker === "complete") {
    return (
      <span className="flex size-4.5 flex-none items-center justify-center rounded-full bg-ok">
        <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true">
          <path d="M2 5.2l2 2L8 2.8" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" className="text-white" />
        </svg>
        <span className="sr-only">{text}</span>
      </span>
    );
  }
  if (marker === "attention") {
    return (
      <span className="flex size-4.5 flex-none items-center justify-center rounded-full bg-warn text-caption font-bold text-white">
        <span aria-hidden="true">!</span>
        <span className="sr-only">{text}</span>
      </span>
    );
  }
  return (
    <span className="m-px size-4 flex-none rounded-full shadow-option">
      <span className="sr-only">{text}</span>
    </span>
  );
}

interface SetupNavProps {
  setup: PracticeSetup;
  selected: SetupNavKey;
}

export function SetupNav({ setup, selected }: SetupNavProps) {
  return (
    <Panel as="nav" aria-label={SETUP_TEXT.sectionsLabel} className="min-w-0 flex-[1_1_15rem] lg:max-w-70">
      <ul className="m-0 list-none p-0">
        {NAV_ORDER.map((key, index) => {
          const active = key === selected;
          return (
            <li key={key} className={index === 0 ? "" : "border-t border-hairline"}>
              <Link
                href={setupSectionPath(key)}
                scroll={false}
                aria-current={active ? "page" : undefined}
                className={`flex h-10 items-center gap-2.5 px-3.5 text-body ${active ? "bg-nav-hover font-medium" : "hover:bg-muted-panel"}`}
              >
                <Marker marker={markerFor(key, setup)} />
                {SETUP_TEXT.sections[key]}
              </Link>
            </li>
          );
        })}
      </ul>
    </Panel>
  );
}
