import type { Metadata } from "next";
import { HqOverviewScreen } from "@/features/hq/overview/HqOverviewScreen";
import { HQ_TEXT } from "@/features/hq/strings";

export const metadata: Metadata = { title: HQ_TEXT.overview.title };

export default function HqOverviewPage() {
  return <HqOverviewScreen />;
}
