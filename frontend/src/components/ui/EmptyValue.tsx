import { FORMAT_WORDS } from "@/lib/format";

export function EmptyValue() {
  return <span className="text-tertiary">{FORMAT_WORDS.empty}</span>;
}
