import type { Metadata } from "next";
import { SetPasswordScreen } from "@/features/set-password/SetPasswordScreen";
import { SET_PASSWORD_TEXT } from "@/features/set-password/strings";

export const metadata: Metadata = { title: SET_PASSWORD_TEXT.pageTitle, robots: { index: false, follow: false } };

export default function SetPasswordPage() {
  return <SetPasswordScreen />;
}
