import type { Metadata } from "next";
import { Suspense } from "react";
import { VERIFY_TEXT } from "@/features/verify/strings";
import { VerifyScreen } from "@/features/verify/VerifyScreen";

export const metadata: Metadata = { title: VERIFY_TEXT.title, robots: { index: false, follow: false } };

export default function VerifyPage() {
  return (
    <Suspense fallback={null}>
      <VerifyScreen />
    </Suspense>
  );
}
