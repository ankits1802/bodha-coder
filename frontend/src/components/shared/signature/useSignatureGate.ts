"use client";

import { useState } from "react";
import { ApiError, UserFacingError } from "@/lib/api/errors";
import { SIGNATURE_TEXT } from "./strings";

export const SIGNATURE_REQUIRED = "signature_required";

interface Waiting {
  retry: () => void;
  cancel: () => void;
}

export interface SignatureGate {
  waiting: boolean;
  gated: <A extends unknown[], R>(call: (...args: A) => Promise<R>) => (...args: A) => Promise<R>;
  adopted: () => void;
  cancel: () => void;
}

export function isSignatureRequired(error: unknown): boolean {
  return error instanceof ApiError && error.code === SIGNATURE_REQUIRED;
}

export function useSignatureGate(): SignatureGate {
  const [waiting, setWaiting] = useState<Waiting | null>(null);

  function gated<A extends unknown[], R>(call: (...args: A) => Promise<R>): (...args: A) => Promise<R> {
    return async (...args: A): Promise<R> => {
      try {
        return await call(...args);
      } catch (error) {
        if (!isSignatureRequired(error)) throw error;
        return new Promise<R>((resolve, reject) => {
          setWaiting({
            retry: () => {
              setWaiting(null);
              call(...args).then(resolve, reject);
            },
            cancel: () => {
              setWaiting(null);
              reject(new UserFacingError(SIGNATURE_TEXT.needed));
            },
          });
        });
      }
    };
  }

  return { waiting: waiting !== null, gated, adopted: () => waiting?.retry(), cancel: () => waiting?.cancel() };
}
