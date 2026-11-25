import type { PracticeSetup } from "@/lib/api/types";
import { MipsSection } from "./MipsSection";
import { ProvidersSection } from "./ProvidersSection";
import { SectionForm } from "./SectionForm";
import type { SetupNavKey } from "./strings";

interface SectionContentProps {
  navKey: SetupNavKey;
  setup: PracticeSetup;
  onSaved: () => void;
}

export function SectionContent({ navKey, setup, onSaved }: SectionContentProps) {
  if (navKey === "mips") return <MipsSection />;
  if (navKey === "providers") return <ProvidersSection missingNpi={setup.missing_npi} onChanged={onSaved} />;
  const section = setup.sections[navKey];
  if (!section) return null;
  return <SectionForm sectionKey={navKey} section={section} onSaved={onSaved} />;
}
