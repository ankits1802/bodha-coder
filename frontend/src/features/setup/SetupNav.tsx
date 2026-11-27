import Link from "next/link";
import { Panel } from "@/components/ui/Panel";
import { StepMark } from "@/components/ui/StepMark";
import { setupSectionPath } from "@/lib/paths";
import type { PracticeSetup } from "@/lib/api/types";
import { NAV_ORDER, markerFor, type SectionMarker } from "./setupModel";
import { SETUP_TEXT, type SetupNavKey } from "./strings";

function Marker({ marker }: { marker: SectionMarker }) {
  if (marker === "none") return <span aria-hidden="true" className="size-4.5 flex-none" />;
  return <StepMark state={marker} label={SETUP_TEXT.marker[marker]} />;
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
