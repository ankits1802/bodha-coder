"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import type { ButtonSize } from "@/components/ui/buttonStyles";
import { Dialog } from "@/components/ui/Dialog";
import { DemoRequestForm } from "./DemoRequestForm";
import { LANDING_TEXT } from "./strings";

export function DemoRequestButton({ size = "lg" }: { size?: ButtonSize }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button variant="primary" size={size} aria-haspopup="dialog" onClick={() => setOpen(true)}>
        {LANDING_TEXT.requestDemo}
      </Button>
      <Dialog open={open} onClose={() => setOpen(false)} title={LANDING_TEXT.form.title}>
        <DemoRequestForm onClose={() => setOpen(false)} />
      </Dialog>
    </>
  );
}
