"use client";

import Link from "next/link";
import { ProviderButtons } from "@/components/shared/sign-in-providers/ProviderButtons";
import { loadedOptions, useSignInOptions } from "@/hooks/useSignInOptions";
import { SIGN_UP_PATH } from "@/lib/api/auth";
import { SIGN_IN_TEXT } from "./strings";

export function OtherWays() {
  const options = loadedOptions(useSignInOptions());
  if (!options) return null;
  return (
    <>
      <ProviderButtons providers={options.providers} />
      {options.signup.enabled ? (
        <p className="m-0 mt-2 text-center text-body text-secondary">
          {SIGN_IN_TEXT.newPractice}{" "}
          <Link href={SIGN_UP_PATH} className="font-medium text-label underline-offset-2 hover:underline">
            {SIGN_IN_TEXT.startTrial}
          </Link>
        </p>
      ) : null}
    </>
  );
}
