import type { ButtonHTMLAttributes, MouseEvent, ReactNode } from "react";
import { buttonClasses, type ButtonSize, type ButtonVariant } from "./buttonStyles";
import { Spinner } from "./Spinner";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  pending?: boolean;
  children: ReactNode;
}

export function Button({
  variant = "secondary",
  size = "md",
  pending = false,
  type = "button",
  disabled,
  className = "",
  onClick,
  children,
  ...rest
}: ButtonProps) {
  function press(event: MouseEvent<HTMLButtonElement>): void {
    if (pending) {
      event.preventDefault();
      return;
    }
    onClick?.(event);
  }

  return (
    <button
      type={type}
      disabled={disabled}
      aria-disabled={pending || undefined}
      aria-busy={pending || undefined}
      onClick={press}
      className={buttonClasses(variant, size, className)}
      {...rest}
    >
      {pending ? <Spinner size="sm" /> : null}
      {children}
    </button>
  );
}
