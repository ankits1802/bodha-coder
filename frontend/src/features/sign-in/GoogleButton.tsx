"use client";

import { buttonClasses } from "@/components/ui/buttonStyles";
import { useRemote } from "@/hooks/useRemote";
import { GOOGLE_START_PATH, getSignInProviders } from "@/lib/api/auth";
import { GoogleMark } from "./GoogleMark";
import { SIGN_IN_TEXT } from "./strings";

export function GoogleButton() {
  const providers = useRemote("sign-in-providers", getSignInProviders);
  if (providers.state.status !== "success" || !providers.state.data.google) return null;
  return (
    <a href={GOOGLE_START_PATH} className={buttonClasses("secondary", "lg", "w-full")}>
      <GoogleMark />
      {SIGN_IN_TEXT.google}
    </a>
  );
}
