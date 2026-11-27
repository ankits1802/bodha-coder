"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import type { ButtonSize, ButtonVariant } from "@/components/ui/buttonStyles";
import { Dialog } from "@/components/ui/Dialog";
import { DemoRequestForm } from "./DemoRequestForm";
import { LANDING_TEXT } from "./strings";

interface DemoRequestButtonProps {
  size?: ButtonSize;
  variant?: ButtonVariant | "link";
}

const LINK_CLASSES = "cursor-pointer border-0 bg-transparent p-0 text-left [font:inherit] [color:inherit] hover:text-label";

export function DemoRequestButton({ size = "lg", variant = "secondary" }: DemoRequestButtonProps) {
  const [open, setOpen] = useState(false);
  const label = LANDING_TEXT.requestDemo;
  return (
    <>
      {variant === "link" ? (
        <button type="button" aria-haspopup="dialog" onClick={() => setOpen(true)} className={LINK_CLASSES}>
          {label}
        </button>
      ) : (
        <Button variant={variant} size={size} aria-haspopup="dialog" onClick={() => setOpen(true)}>
          {label}
        </Button>
      )}
      <Dialog open={open} onClose={() => setOpen(false)} title={LANDING_TEXT.form.title}>
        <DemoRequestForm onClose={() => setOpen(false)} />
      </Dialog>
    </>
  );
}
