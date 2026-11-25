import type { Metadata } from "next";
import { TodayScreen } from "@/features/today/TodayScreen";
import { TODAY_TEXT } from "@/features/today/strings";

export const metadata: Metadata = { title: TODAY_TEXT.title };

export default function TodayPage() {
  return <TodayScreen />;
}
