interface ChevronProps {
  direction?: "left" | "right" | "down";
  className?: string;
}

const SHAPES = {
  right: { width: 8, height: 13, path: "M1.5 1.5l5 5-5 5" },
  left: { width: 8, height: 13, path: "M6.5 1.5l-5 5 5 5" },
  down: { width: 13, height: 8, path: "M1.5 1.5l5 5 5-5" },
} as const;

export function Chevron({ direction = "right", className = "flex-none text-chevron" }: ChevronProps) {
  const shape = SHAPES[direction];
  return (
    <svg width={shape.width} height={shape.height} viewBox={`0 0 ${shape.width} ${shape.height}`} aria-hidden="true" className={className}>
      <path d={shape.path} fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
