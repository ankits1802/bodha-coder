"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback } from "react";

export type QueryChanges = Record<string, string | null>;

export interface QueryParams {
  get: (name: string) => string | null;
  update: (changes: QueryChanges) => void;
}

export function useQueryParams(): QueryParams {
  const searchParams = useSearchParams();
  const pathname = usePathname();
  const router = useRouter();

  const update = useCallback(
    (changes: QueryChanges) => {
      const next = new URLSearchParams(searchParams.toString());
      for (const [name, value] of Object.entries(changes)) {
        if (value === null || value === "") next.delete(name);
        else next.set(name, value);
      }
      const search = next.toString();
      router.replace(search ? `${pathname}?${search}` : pathname, { scroll: false });
    },
    [pathname, router, searchParams],
  );

  return { get: (name) => searchParams.get(name), update };
}
