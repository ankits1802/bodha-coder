import type { Metadata } from "next";
import { Suspense } from "react";
import { AreaGuard } from "@/components/shared/AreaGuard";
import { LoadingState } from "@/components/ui/LoadingState";
import { TEAM_TEXT } from "@/features/team/strings";
import { TeamScreen } from "@/features/team/TeamScreen";

export const metadata: Metadata = { title: TEAM_TEXT.title };

export default function TeamPage() {
  return (
    <AreaGuard area="team">
      <Suspense fallback={<LoadingState label={TEAM_TEXT.loading} />}>
        <TeamScreen />
      </Suspense>
    </AreaGuard>
  );
}
