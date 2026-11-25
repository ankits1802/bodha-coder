export type CodeChipVariant = "default" | "old" | "new";

const VARIANTS: Record<CodeChipVariant, string> = {
  default: "bg-chip text-label font-semibold",
  old: "bg-transparent text-tertiary font-medium line-through",
  new: "bg-surface text-label font-semibold shadow-code-new",
};

interface CodeChipProps {
  code: string;
  variant?: CodeChipVariant;
  className?: string;
}

export function CodeChip({ code, variant = "default", className = "" }: CodeChipProps) {
  return (
    <span className={`rounded-chip px-1.75 py-0.5 text-footnote tabular-nums tracking-normal whitespace-nowrap ${VARIANTS[variant]} ${className}`}>
      {code}
    </span>
  );
}
