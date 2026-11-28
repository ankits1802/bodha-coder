"use client";

import { useState } from "react";
import { SignatureDialog } from "@/components/shared/signature/SignatureDialog";
import { SignaturePicture } from "@/components/shared/signature/SignaturePicture";
import { SIGNATURE_TEXT } from "@/components/shared/signature/strings";
import { Button } from "@/components/ui/Button";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { RemoteView } from "@/components/ui/RemoteView";
import { useRemote } from "@/hooks/useRemote";
import { getMySignature } from "@/lib/api/signatures";
import { canDo } from "@/lib/roles";
import { useSession } from "@/lib/session/useSession";

const REMOTE_TEXT = { loading: SIGNATURE_TEXT.loading, empty: "", retry: SIGNATURE_TEXT.retry };

function MySignatureCard() {
  const remote = useRemote("signature", getMySignature);
  const [open, setOpen] = useState(false);
  const saved = remote.state.status === "success" ? remote.state.data.signature : null;

  return (
    <Panel aria-label={SIGNATURE_TEXT.title} className="max-w-180">
      <PanelHeader
        title={SIGNATURE_TEXT.title}
        actions={
          <Button size="sm" onClick={() => setOpen(true)}>
            {saved ? SIGNATURE_TEXT.replace : SIGNATURE_TEXT.add}
          </Button>
        }
      />
      <RemoteView state={remote.state} text={REMOTE_TEXT} onRetry={remote.reload}>
        {({ signature }) => (
          <div className="px-4.5 pb-4">
            <SignaturePicture src={signature?.image ?? null} alt={SIGNATURE_TEXT.preview(signature?.typed_name ?? "")}>
              <span className="text-subhead text-ink-soft">{SIGNATURE_TEXT.none}</span>
            </SignaturePicture>
          </div>
        )}
      </RemoteView>
      <SignatureDialog
        open={open}
        onClose={() => setOpen(false)}
        onAdopted={(signature) => {
          remote.replace({ signature });
          setOpen(false);
        }}
      />
    </Panel>
  );
}

export function SignaturePanel() {
  const { user } = useSession();
  return canDo(user?.role, "sign") ? <MySignatureCard /> : null;
}
