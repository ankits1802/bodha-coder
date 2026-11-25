import type { InputHTMLAttributes, SelectHTMLAttributes, TextareaHTMLAttributes } from "react";

const CONTROL =
  "w-full rounded-control bg-surface text-body text-label shadow-field outline-none transition-shadow placeholder:text-tertiary focus:shadow-field-focus aria-invalid:shadow-field-error disabled:bg-muted-panel disabled:text-tertiary";

export function Input({ className = "", ...rest }: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={`${CONTROL} h-9 px-3 ${className}`} {...rest} />;
}

export function Select({ className = "", children, ...rest }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select className={`${CONTROL} h-9 appearance-auto px-3 ${className}`} {...rest}>
      {children}
    </select>
  );
}

export function TextArea({ className = "", ...rest }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={`${CONTROL} min-h-16 resize-y px-3 py-2 ${className}`} {...rest} />;
}
