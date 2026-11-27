"use client";

import { Dialog } from "@/components/ui/Dialog";
import type { SignatureView } from "@/lib/api/types";
import { useSession } from "@/lib/session/useSession";
import { SignatureSetup } from "./SignatureSetup";
import { SIGNATURE_TEXT } from "./strings";
import type { SignatureGate } from "./useSignatureGate";

interface SignatureDialogProps {
  open: boolean;
  onClose: () => void;
  onAdopted: (signature: SignatureView) => void;
}

export function SignatureDialog({ open, onClose, onAdopted }: SignatureDialogProps) {
  const { user } = useSession();
  return (
    <Dialog open={open} onClose={onClose} title={SIGNATURE_TEXT.addTitle} size="lg">
      {open ? <SignatureSetup defaultName={user?.name ?? ""} onAdopted={onAdopted} /> : null}
    </Dialog>
  );
}

export function SignatureGateDialog({ gate }: { gate: SignatureGate }) {
  return <SignatureDialog open={gate.waiting} onClose={gate.cancel} onAdopted={gate.adopted} />;
}
