export type ButtonVariant = "primary" | "secondary" | "plain" | "danger";
export type ButtonSize = "sm" | "md" | "lg";

const BASE =
  "inline-flex items-center justify-center gap-1.5 rounded-full font-medium tracking-snug whitespace-nowrap transition-colors disabled:cursor-not-allowed aria-disabled:cursor-not-allowed";

const VARIANTS: Record<ButtonVariant, string> = {
  primary: "bg-primary text-white hover:bg-primary-hover disabled:bg-disabled aria-disabled:bg-disabled",
  secondary:
    "bg-fill text-label hover:bg-fill-hover disabled:text-tertiary disabled:hover:bg-fill aria-disabled:text-tertiary aria-disabled:hover:bg-fill",
  plain:
    "bg-transparent text-label hover:bg-fill-plain-hover disabled:text-tertiary disabled:hover:bg-transparent aria-disabled:text-tertiary aria-disabled:hover:bg-transparent",
  danger:
    "bg-transparent text-bad-text hover:bg-fill-plain-hover disabled:text-tertiary disabled:hover:bg-transparent aria-disabled:text-tertiary aria-disabled:hover:bg-transparent",
};

const SIZES: Record<ButtonSize, string> = {
  sm: "h-8 px-4 text-body",
  md: "h-9 px-4.5 text-body",
  lg: "h-11.5 px-6 text-input",
};

export function buttonClasses(variant: ButtonVariant = "secondary", size: ButtonSize = "md", extra = ""): string {
  return [BASE, VARIANTS[variant], SIZES[size], extra].filter(Boolean).join(" ");
}
