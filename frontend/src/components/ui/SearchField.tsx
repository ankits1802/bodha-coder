import type { InputHTMLAttributes } from "react";

interface SearchFieldProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "type"> {
  label: string;
}

export function SearchField({ label, className = "", ...rest }: SearchFieldProps) {
  return (
    <label className={`flex h-7.5 w-55 max-w-full items-center gap-1.5 rounded-control bg-control px-2.5 text-tertiary ${className}`}>
      <svg width="13" height="13" viewBox="0 0 14 14" aria-hidden="true">
        <circle cx="6" cy="6" r="4.2" fill="none" stroke="currentColor" strokeWidth="1.5" />
        <path d="M9.2 9.2L12.5 12.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
      <span className="sr-only">{label}</span>
      <input
        type="search"
        placeholder={label}
        className="min-w-0 flex-1 border-0 bg-transparent text-subhead text-label outline-none placeholder:text-tertiary"
        {...rest}
      />
    </label>
  );
}
