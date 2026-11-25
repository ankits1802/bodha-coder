import type { Metadata } from "next";
import { ForgotPasswordScreen } from "@/features/forgot-password/ForgotPasswordScreen";
import { FORGOT_PASSWORD_TEXT } from "@/features/forgot-password/strings";

export const metadata: Metadata = { title: FORGOT_PASSWORD_TEXT.pageTitle, robots: { index: false, follow: false } };

export default function ForgotPasswordPage() {
  return <ForgotPasswordScreen />;
}
