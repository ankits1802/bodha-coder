import type { SelectHTMLAttributes } from "react";

interface FilterSelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string;
}

export function FilterSelect({ label, className = "", children, ...rest }: FilterSelectProps) {
  return (
    <label className="inline-flex">
      <span className="sr-only">{label}</span>
      <select
        className={`h-7.5 cursor-pointer rounded-control bg-surface pr-2.5 pl-3 text-subhead text-label shadow-pop outline-none ${className}`}
        {...rest}
      >
        {children}
      </select>
    </label>
  );
}
