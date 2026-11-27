import type { PracticeSetup } from "@/lib/api/types";
import { MipsSection } from "./MipsSection";
import { PayersPanel } from "./PayersPanel";
import { ProvidersSection } from "./ProvidersSection";
import { SectionForm } from "./SectionForm";
import type { SetupNavKey } from "./strings";

interface SectionContentProps {
  navKey: SetupNavKey;
  setup: PracticeSetup;
  onSaved: () => void;
  onSectionSaved: () => void;
}

export function SectionContent({ navKey, setup, onSaved, onSectionSaved }: SectionContentProps) {
  if (navKey === "mips") return <MipsSection />;
  if (navKey === "providers") return <ProvidersSection missingNpi={setup.missing_npi} onChanged={onSaved} />;
  const section = setup.sections[navKey];
  if (!section) return null;
  const form = <SectionForm sectionKey={navKey} section={section} onSaved={onSectionSaved} />;
  if (navKey !== "payers") return form;
  return (
    <>
      {form}
      <PayersPanel payers={setup.payers} onChanged={onSaved} />
    </>
  );
}
