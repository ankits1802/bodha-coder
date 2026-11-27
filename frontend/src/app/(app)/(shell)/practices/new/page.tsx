import type { Metadata } from "next";
import { AreaGuard } from "@/components/shared/AreaGuard";
import { NewPracticeScreen } from "@/features/sign-up/NewPracticeScreen";
import { SIGN_UP_TEXT } from "@/features/sign-up/strings";

export const metadata: Metadata = { title: SIGN_UP_TEXT.newPracticeTitle };

export default function NewPracticePage() {
  return (
    <AreaGuard area="security">
      <NewPracticeScreen />
    </AreaGuard>
  );
}
