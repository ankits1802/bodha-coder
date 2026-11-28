import { EmailIntake } from "@/components/shared/intake/EmailIntake";
import { IntakeSettings } from "@/components/shared/intake/IntakeSettings";
import type { PracticeSetup } from "@/lib/api/types";
import type { SetupOpen } from "@/lib/paths";
import { ChargesPanel } from "./ChargesPanel";
import { ChecksPanel } from "./ChecksPanel";
import { ClearinghouseSection } from "./ClearinghouseSection";
import { MipsSection } from "./MipsSection";
import { PayersPanel } from "./PayersPanel";
import { ProvidersSection } from "./ProvidersSection";
import { ReviewSettingsPanel } from "./ReviewSettingsPanel";
import { SectionForm } from "./SectionForm";
import type { SetupNavKey } from "./strings";

interface SectionContentProps {
  navKey: SetupNavKey;
  setup: PracticeSetup;
  open: SetupOpen | null;
  onOpened: () => void;
  onSaved: () => void;
  onSectionSaved: () => void;
}

function PayersSection({ setup, open, onOpened, onSaved, onSectionSaved }: Omit<SectionContentProps, "navKey">) {
  const section = setup.sections.payers;
  return (
    <>
      <PayersPanel payers={setup.payers} addOnArrival={open === "addPayer"} onArrived={onOpened} onChanged={onSaved} />
      <SectionForm sectionKey="payers" section={section} onSaved={onSectionSaved} />
    </>
  );
}

export function SectionContent(props: SectionContentProps) {
  const { navKey, setup, open, onOpened, onSaved, onSectionSaved } = props;
  if (navKey === "mips") return <MipsSection />;
  if (navKey === "clearinghouse") return <ClearinghouseSection />;
  if (navKey === "intake") {
    return (
      <>
        <EmailIntake />
        <IntakeSettings />
      </>
    );
  }
  if (navKey === "checks") {
    return (
      <>
        <ChecksPanel checks={setup.checks} onSaved={onSaved} />
        <ReviewSettingsPanel settings={setup.review} onSaved={onSaved} />
      </>
    );
  }
  if (navKey === "providers") {
    return <ProvidersSection missingNpi={setup.missing_npi} open={open} onOpened={onOpened} onChanged={onSaved} />;
  }
  if (navKey === "payers") return <PayersSection {...props} />;
  if (navKey === "payments") {
    return (
      <>
        <ChargesPanel />
        <SectionForm sectionKey="payments" section={setup.sections.payments} onSaved={onSectionSaved} />
      </>
    );
  }
  const section = setup.sections[navKey];
  return section ? <SectionForm sectionKey={navKey} section={section} onSaved={onSectionSaved} /> : null;
}
