import type { Metadata } from "next";
import { PracticeCompletionScreen } from "@/features/sign-up/PracticeCompletionScreen";
import { SIGN_UP_TEXT } from "@/features/sign-up/strings";

export const metadata: Metadata = { title: SIGN_UP_TEXT.completeTitle, robots: { index: false, follow: false } };

export default function PracticeSignUpPage() {
  return <PracticeCompletionScreen />;
}
