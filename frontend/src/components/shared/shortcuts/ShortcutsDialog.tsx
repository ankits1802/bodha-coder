"use client";

import { usePathname } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { useSession } from "@/lib/session/useSession";
import { closeOverlay, openOverlay, useOpenOverlay } from "../overlays";
import { SHARED_TEXT } from "../strings";
import { scopeForPath, type ShortcutScope } from "./registry";
import { ShortcutList } from "./ShortcutList";
import { useShortcuts } from "./useShortcuts";

function scopesFor(pathname: string): ShortcutScope[] {
  const scope = scopeForPath(pathname);
  return scope === "global" ? ["global"] : [scope, "global"];
}

export function ShortcutsDialog() {
  const { user } = useSession();
  const pathname = usePathname();
  const open = useOpenOverlay() === "shortcuts";
  const words = SHARED_TEXT.shortcuts;
  useShortcuts("global", { shortcuts: () => openOverlay("shortcuts") });
  if (!user) return null;

  return (
    <Dialog
      open={open}
      onClose={closeOverlay}
      title={words.title}
      footer={<Button onClick={closeOverlay}>{words.close}</Button>}
    >
      <ShortcutList scopes={scopesFor(pathname)} role={user.role} />
    </Dialog>
  );
}
