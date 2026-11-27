"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useEffectEvent, useState } from "react";
import type { User } from "@/lib/api/types";
import { canReach } from "@/lib/roles";
import { handOffFiles, isPdf } from "./droppedFiles";
import { UPLOAD_DROP_TEXT } from "./strings";

export const UPLOAD_PATH = "/upload";

function carriesFiles(event: DragEvent): boolean {
  return Array.from(event.dataTransfer?.types ?? []).includes("Files");
}

export function DropOverlay({ user }: { user: User }) {
  const router = useRouter();
  const pathname = usePathname();
  const [showing, setShowing] = useState(false);
  const allowed = canReach(user, "upload");
  const dropped = useEffectEvent((files: File[]) => {
    if (!files.some(isPdf)) return;
    handOffFiles(files);
    if (pathname !== UPLOAD_PATH) router.push(UPLOAD_PATH);
  });

  useEffect(() => {
    if (!allowed) return;
    let depth = 0;
    const enter = (event: DragEvent) => {
      if (!carriesFiles(event)) return;
      event.preventDefault();
      depth += 1;
      setShowing(true);
    };
    const over = (event: DragEvent) => {
      if (carriesFiles(event)) event.preventDefault();
    };
    const leave = (event: DragEvent) => {
      if (!carriesFiles(event)) return;
      depth = Math.max(0, depth - 1);
      if (depth === 0) setShowing(false);
    };
    const drop = (event: DragEvent) => {
      if (!carriesFiles(event)) return;
      event.preventDefault();
      depth = 0;
      setShowing(false);
      dropped(Array.from(event.dataTransfer?.files ?? []));
    };
    const listeners = { dragenter: enter, dragover: over, dragleave: leave, drop } as const;
    for (const [name, listener] of Object.entries(listeners)) window.addEventListener(name, listener as EventListener);
    return () => {
      for (const [name, listener] of Object.entries(listeners)) window.removeEventListener(name, listener as EventListener);
    };
  }, [allowed]);

  if (!allowed || !showing) return null;
  return (
    <div className="pointer-events-none fixed inset-0 z-50 flex items-center justify-center bg-surface/90 p-6">
      <p role="status" className="m-0 rounded-panel border-2 border-dashed border-separator bg-surface px-10 py-12 text-title3 font-semibold text-label shadow-float">
        {UPLOAD_DROP_TEXT.drop}
      </p>
    </div>
  );
}
