import type { ButtonHTMLAttributes, ReactNode } from "react";

interface TextButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  tone?: "label" | "warn";
  children: ReactNode;
}

const TONES = { label: "text-label", warn: "text-warn-text" } as const;

export function TextButton({ tone = "label", type = "button", className = "", children, ...rest }: TextButtonProps) {
  return (
    <button
      type={type}
      className={`cursor-pointer border-0 bg-transparent p-0 font-medium underline underline-offset-2 disabled:cursor-wait disabled:text-tertiary ${TONES[tone]} ${className}`}
      {...rest}
    >
      {children}
    </button>
  );
}
