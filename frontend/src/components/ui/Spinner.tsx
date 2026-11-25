interface SpinnerProps {
  label?: string;
  size?: "sm" | "md";
}

const SIZES = { sm: "size-3.5 border-2", md: "size-5 border-2" } as const;

export function Spinner({ label, size = "md" }: SpinnerProps) {
  return (
    <span className="inline-flex items-center gap-2 text-secondary" role={label ? "status" : undefined}>
      <span
        aria-hidden="true"
        className={`${SIZES[size]} animate-spin rounded-full border-current border-r-transparent motion-reduce:animate-none`}
      />
      {label ? <span className="text-subhead">{label}</span> : null}
    </span>
  );
}
