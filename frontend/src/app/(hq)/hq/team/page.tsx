import type { Metadata } from "next";
import { HqTeamScreen } from "@/features/hq/team/HqTeamScreen";
import { HQ_TEXT } from "@/features/hq/strings";

export const metadata: Metadata = { title: HQ_TEXT.team.title };

export default function HqTeamPage() {
  return <HqTeamScreen />;
}
