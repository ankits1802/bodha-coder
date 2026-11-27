import type { Metadata } from "next";
import { HelpScreen } from "@/features/help/HelpScreen";
import { HELP_TEXT } from "@/features/help/strings";

export const metadata: Metadata = { title: HELP_TEXT.pageTitle };

export default function HelpPage() {
  return <HelpScreen />;
}
