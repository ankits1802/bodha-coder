interface ProgressBarProps {
  label: string;
  value: number;
  max: number;
  tone?: "neutral" | "ok";
}

export function ProgressBar({ label, value, max, tone = "neutral" }: ProgressBarProps) {
  const share = max > 0 ? Math.min(100, Math.round((value / max) * 100)) : 0;
  return (
    <span
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={max}
      aria-valuenow={value}
      className="block h-1 overflow-hidden rounded-full bg-hairline"
    >
      <span
        className={`block h-full rounded-full ${tone === "ok" ? "bg-ok" : "bg-chart-bar"}`}
        style={{ width: `${share}%` }}
      />
    </span>
  );
}
