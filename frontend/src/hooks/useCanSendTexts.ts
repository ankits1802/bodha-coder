"use client";

import { useSession } from "@/lib/session/useSession";

export function useCanSendTexts(): boolean {
  return useSession().user?.practice?.can_send_texts ?? false;
}
