"use client";

import { useEffect } from "react";
import { endSession, refreshSession } from "@/lib/api/client";

const WEBHOOK_WAIT_MS = 4000;
const BILLING_ONLY_CHECKS = 5;

interface CheckoutReturn {
  done: boolean;
  billingOnly: boolean;
  reload: () => void;
}

function renewSession(): void {
  refreshSession().then(
    (ok) => {
      if (!ok) endSession();
    },
    () => undefined,
  );
}

export function useCheckoutReturn({ done, billingOnly, reload }: CheckoutReturn): void {
  useEffect(() => {
    if (!done) return;
    let checks = 0;
    const timer = window.setInterval(() => {
      checks += 1;
      reload();
      if (billingOnly) renewSession();
      if (!billingOnly || checks >= BILLING_ONLY_CHECKS) window.clearInterval(timer);
    }, WEBHOOK_WAIT_MS);
    return () => window.clearInterval(timer);
  }, [done, billingOnly, reload]);
}
