import { useId, type ReactNode } from "react";

export interface FieldControlProps {
  id: string;
  "aria-describedby"?: string;
  "aria-invalid"?: boolean;
}

export function fieldLabelId(controlId: string): string {
  return `${controlId}-label`;
}

interface FieldProps {
  label: ReactNode;
  error?: string | null;
  hint?: ReactNode;
  optional?: ReactNode;
  className?: string;
  children: (control: FieldControlProps) => ReactNode;
}

export function Field({ label, error, hint, optional, className = "", children }: FieldProps) {
  const id = useId();
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [hintId, errorId].filter(Boolean).join(" ") || undefined;
  return (
    <div className={`flex flex-col gap-1.5 ${className}`}>
      <label id={fieldLabelId(id)} htmlFor={id} className="text-subhead font-medium text-label">
        {label}
        {optional ? (
          <>
            <span className="sr-only">,</span>{" "}
            <span className="font-normal text-tertiary">{optional}</span>
          </>
        ) : null}
      </label>
      {children({ id, "aria-describedby": describedBy, "aria-invalid": error ? true : undefined })}
      {hint ? (
        <span id={hintId} className="text-caption text-secondary">
          {hint}
        </span>
      ) : null}
      {error ? (
        <span id={errorId} className="text-footnote text-bad-text">
          {error}
        </span>
      ) : null}
    </div>
  );
}
