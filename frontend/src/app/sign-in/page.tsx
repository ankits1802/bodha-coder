import type { Metadata } from "next";
import { Suspense } from "react";
import { AuthFrame } from "@/components/shared/AuthFrame";
import { SignInScreen } from "@/features/sign-in/SignInScreen";
import { SIGN_IN_TEXT } from "@/features/sign-in/strings";

export const metadata: Metadata = { title: SIGN_IN_TEXT.title, robots: { index: false, follow: false } };

export default function SignInPage() {
  return (
    <Suspense fallback={<AuthFrame>{null}</AuthFrame>}>
      <SignInScreen />
    </Suspense>
  );
}
