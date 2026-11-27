import type { InputHTMLAttributes, TextareaHTMLAttributes } from "react";
import { FIELD_CLASSES } from "./fieldStyles";

export const CONTROL = `w-full ${FIELD_CLASSES}`;

export function Input({ className = "", ...rest }: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={`${CONTROL} h-9 px-3 ${className}`} {...rest} />;
}

export function TextArea({ className = "", ...rest }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={`${CONTROL} min-h-16 resize-y px-3 py-2 ${className}`} {...rest} />;
}
