import type { ReactNode } from "react";
import { SECTION_IDS } from "../anchors";
import { LANDING_TEXT } from "../strings";
import { DeskPanel } from "./DeskPanel";
import { DeskTabs } from "./DeskTabs";
import { AdminUi } from "./ui/AdminUi";
import { BillingUi } from "./ui/BillingUi";
import { ComplianceUi } from "./ui/ComplianceUi";
import { PhoneUi } from "./ui/PhoneUi";
import { QueryUi } from "./ui/QueryUi";
import { QueueUi } from "./ui/QueueUi";

const DESKS = ["coders", "cdi", "compliance", "billers", "providers", "admins"] as const;

type Desk = (typeof DESKS)[number];

const VISUALS: Record<Desk, () => ReactNode> = {
  coders: QueueUi,
  cdi: QueryUi,
  compliance: ComplianceUi,
  billers: BillingUi,
  providers: PhoneUi,
  admins: AdminUi,
};

export function Desks() {
  const words = LANDING_TEXT.desks;
  const tabs = DESKS.map((desk) => {
    const Visual = VISUALS[desk];
    const role = words[desk];
    return { key: desk, label: role.tab, panel: <DeskPanel title={role.title} points={role.points} visual={<Visual />} /> };
  });
  return (
    <section id={SECTION_IDS.teams} aria-labelledby="teams-title" className="scroll-mt-16 px-6 py-28 sm:py-32">
      <div className="mx-auto max-w-landing">
        <div className="text-center">
          <h2 id="teams-title" data-reveal="" className="m-0 font-display text-hero-sm font-bold tracking-display sm:text-display">
            {words.title}
          </h2>
          <p data-reveal="" className="mt-4 mb-0 text-title3 text-secondary">
            {words.lead}
          </p>
        </div>
        <div data-reveal="" className="mt-12">
          <DeskTabs label={words.tabsLabel} tabs={tabs} />
        </div>
      </div>
    </section>
  );
}
