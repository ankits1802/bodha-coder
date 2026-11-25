import type { Metadata } from "next";
import { RespondScreen } from "@/features/respond/RespondScreen";
import { RESPOND_TEXT } from "@/features/respond/strings";

export const metadata: Metadata = { title: RESPOND_TEXT.pageTitle, robots: { index: false, follow: false } };

export default function RespondPage() {
  return <RespondScreen />;
}
