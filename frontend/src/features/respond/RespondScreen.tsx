"use client";

import { useState, type ReactNode } from "react";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { useFragmentToken } from "@/hooks/useFragmentToken";
import { RequestView } from "./RequestView";
import { RESPOND_TEXT } from "./strings";
import { TopBar } from "./TopBar";
import { VerifyPanel } from "./VerifyPanel";

type Stage = { kind: "verify"; expired: boolean } | { kind: "request"; providerToken: string };

function Frame({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col bg-page">
      <TopBar />
      <main className="flex-1 px-4">{children}</main>
    </div>
  );
}

export function RespondScreen() {
  const token = useFragmentToken();
  const [stage, setStage] = useState<Stage>({ kind: "verify", expired: false });

  if (token === undefined) {
    return (
      <Frame>
        <LoadingState label={RESPOND_TEXT.loading} />
      </Frame>
    );
  }
  if (token === null) {
    return (
      <Frame>
        <ErrorState message={RESPOND_TEXT.invalidLink} />
      </Frame>
    );
  }
  if (stage.kind === "request") {
    return (
      <RequestView
        key={stage.providerToken}
        providerToken={stage.providerToken}
        onExpired={() => setStage({ kind: "verify", expired: true })}
        onSwitch={(providerToken) => setStage({ kind: "request", providerToken })}
      />
    );
  }
  return (
    <Frame>
      <VerifyPanel
        token={token}
        expired={stage.expired}
        onVerified={(providerToken) => setStage({ kind: "request", providerToken })}
      />
    </Frame>
  );
}
