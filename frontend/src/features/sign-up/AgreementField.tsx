import { AgreementCheck } from "@/components/shared/agreement/AgreementCheck";
import type { SignUpOptions } from "@/lib/api/types";
import type { DraftForm } from "./useSignUpDraft";

export function AgreementField({ form, options }: { form: DraftForm; options: SignUpOptions }) {
  return (
    <AgreementCheck
      options={options}
      checked={form.draft.agreed}
      error={form.errors.agreed}
      onChange={(checked) => form.change("agreed", checked)}
      onBlur={() => form.touch("agreed")}
    />
  );
}
