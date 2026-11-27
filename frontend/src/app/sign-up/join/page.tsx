import type { Metadata } from "next";
import { JoinScreen } from "@/features/sign-up/JoinScreen";
import { SIGN_UP_TEXT } from "@/features/sign-up/strings";

export const metadata: Metadata = { title: SIGN_UP_TEXT.completeTitle, robots: { index: false, follow: false } };

export default function JoinSignUpPage() {
  return <JoinScreen />;
}
