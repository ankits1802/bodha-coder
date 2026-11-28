"use client";

import { useEffect, useState } from "react";
import { discoverSso } from "@/lib/api/sso";
import type { SsoDiscovery } from "@/lib/api/types";

export const DISCOVERY_DELAY_MS = 400;
const EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
export const NO_SSO: SsoDiscovery = { mode: "none", start_url: null };

interface Found {
  email: string;
  discovery: SsoDiscovery;
}

export function useSsoDiscovery(email: string): SsoDiscovery {
  const [found, setFound] = useState<Found | null>(null);
  const address = email.trim().toLowerCase();

  useEffect(() => {
    if (!EMAIL.test(address)) return;
    let live = true;
    const timer = window.setTimeout(() => {
      discoverSso(address).then(
        (discovery) => {
          if (live) setFound({ email: address, discovery });
        },
        () => {
          if (live) setFound({ email: address, discovery: NO_SSO });
        },
      );
    }, DISCOVERY_DELAY_MS);
    return () => {
      live = false;
      window.clearTimeout(timer);
    };
  }, [address]);

  return found?.email === address ? found.discovery : NO_SSO;
}
