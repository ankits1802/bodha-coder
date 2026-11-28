import type { SelectOption } from "@/components/ui/Select";
import type { FilePreview, PayerOption } from "@/lib/api/types";
import { UPLOAD_TEXT } from "./strings";
import type { References, UploadEntry } from "./uploadEntries";

export type PayerSource = "person" | "document" | "provider";
export type PayerFields = Pick<UploadEntry, "payerId" | "payerSource" | "suggestedPayer">;

export const MIXED_PAYER = "mixed";

const words = UPLOAD_TEXT.payer;

export function usualPayer(providerId: string, references: References): string | null {
  const provider = references.providers.find((item) => item.id === providerId);
  const payer = provider?.payer ?? null;
  return payer && references.payers.some((item) => item.id === payer) ? payer : null;
}

function fromProvider(providerId: string, references: References): Pick<UploadEntry, "payerId" | "payerSource"> {
  const usual = usualPayer(providerId, references);
  return { payerId: usual ?? "", payerSource: usual ? "provider" : null };
}

export function previewPayer(entry: UploadEntry, preview: FilePreview, providerId: string, references: References): PayerFields {
  const suggestedPayer = preview.payer_confident ? null : preview.payer_id;
  if (entry.payerSource === "person") return { payerId: entry.payerId, payerSource: "person", suggestedPayer };
  if (preview.payer_confident && preview.payer_id) return { payerId: preview.payer_id, payerSource: "document", suggestedPayer };
  return { ...fromProvider(providerId, references), suggestedPayer };
}

export function providerPayer(entry: UploadEntry, providerId: string, references: References): Pick<UploadEntry, "payerId" | "payerSource"> {
  if (entry.payerSource === "person" || entry.payerSource === "document") return { payerId: entry.payerId, payerSource: entry.payerSource };
  return fromProvider(providerId, references);
}

export function chosenPayer(entry: UploadEntry, payerId: string): UploadEntry {
  return { ...entry, payerId, payerSource: "person" };
}

export function sharedPayer(entries: UploadEntry[]): string | null {
  const values = new Set(entries.map((entry) => entry.payerId));
  const [only] = values;
  return values.size <= 1 ? (only ?? "") : null;
}

export function payerOptions(payers: PayerOption[], suggested: string | null = null): SelectOption[] {
  const hint = payers.find((payer) => payer.id === suggested);
  const none: SelectOption = { value: "", label: words.none };
  if (!hint) return [none, ...payers.map((payer) => ({ value: payer.id, label: payer.name }))];
  const rest = payers.filter((payer) => payer.id !== hint.id);
  return [
    none,
    { value: hint.id, label: hint.name, group: words.suggested },
    ...rest.map((payer) => ({ value: payer.id, label: payer.name, group: words.all })),
  ];
}

export function batchPayerOptions(payers: PayerOption[], shared: string | null): SelectOption[] {
  const options = payerOptions(payers);
  return shared === null ? [{ value: MIXED_PAYER, label: UPLOAD_TEXT.plan.mixed, disabled: true }, ...options] : options;
}
