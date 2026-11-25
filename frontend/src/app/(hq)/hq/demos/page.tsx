import type { Metadata } from "next";
import { HqDemosScreen } from "@/features/hq/demos/HqDemosScreen";
import { HQ_TEXT } from "@/features/hq/strings";

export const metadata: Metadata = { title: HQ_TEXT.demos.title };

export default function HqDemosPage() {
  return <HqDemosScreen />;
}
