import type { Metadata } from "next";
import { SignUpScreen } from "@/features/sign-up/SignUpScreen";
import { SIGN_UP_TEXT } from "@/features/sign-up/strings";

export const metadata: Metadata = { title: SIGN_UP_TEXT.pageTitle };

export default function SignUpPage() {
  return <SignUpScreen />;
}
