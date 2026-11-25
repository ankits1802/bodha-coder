interface ChevronProps {
  direction?: "left" | "right";
  className?: string;
}

const PATHS = {
  right: "M1.5 1.5l5 5-5 5",
  left: "M6.5 1.5l-5 5 5 5",
} as const;

export function Chevron({ direction = "right", className = "flex-none text-chevron" }: ChevronProps) {
  return (
    <svg width="8" height="13" viewBox="0 0 8 13" aria-hidden="true" className={className}>
      <path d={PATHS[direction]} fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
