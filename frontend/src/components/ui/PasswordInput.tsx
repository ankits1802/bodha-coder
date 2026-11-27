"use client";

import { useRef, useState, type InputHTMLAttributes } from "react";
import { SHARED_TEXT } from "@/components/shared/strings";
import { CONTROL } from "./Input";

export type PasswordLook = "boxed" | "bare";

interface PasswordInputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "type"> {
  look?: PasswordLook;
}

const LOOKS: Record<PasswordLook, string> = {
  boxed: `${CONTROL} h-9 pl-3 pr-10`,
  bare: "pr-9",
};

function EyeIcon({ open }: { open: boolean }) {
  return (
    <svg aria-hidden="true" viewBox="0 0 20 20" className="size-4.5" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M1.8 10s3-5.6 8.2-5.6 8.2 5.6 8.2 5.6-3 5.6-8.2 5.6S1.8 10 1.8 10z" strokeLinejoin="round" />
      <circle cx="10" cy="10" r="2.6" />
      {open ? null : <path d="M3.5 16.5l13-13" strokeLinecap="round" />}
    </svg>
  );
}

export function PasswordInput({ look = "boxed", className = "", ...rest }: PasswordInputProps) {
  const [shown, setShown] = useState(false);
  const field = useRef<HTMLInputElement>(null);
  const words = SHARED_TEXT.password;

  function toggle(): void {
    setShown((current) => !current);
    field.current?.focus();
  }

  return (
    <span className="relative flex w-full items-center">
      <input ref={field} {...rest} type={shown ? "text" : "password"} className={`${LOOKS[look]} ${className}`} />
      <button
        type="button"
        aria-label={shown ? words.hide : words.show}
        aria-pressed={shown}
        onMouseDown={(event) => event.preventDefault()}
        onClick={toggle}
        className="absolute right-1 inline-flex size-8 cursor-pointer items-center justify-center rounded-control border-0 bg-transparent text-secondary hover:text-label"
      >
        <EyeIcon open={!shown} />
      </button>
    </span>
  );
}
