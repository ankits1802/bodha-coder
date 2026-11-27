import type { Metadata } from "next";
import { Suspense } from "react";
import { RemittancesScreen } from "@/features/remittances/RemittancesScreen";
import { REMITTANCE_TEXT } from "@/features/remittances/strings";

export const metadata: Metadata = { title: REMITTANCE_TEXT.title };

export default function RemittancesPage() {
  return (
    <Suspense>
      <RemittancesScreen />
    </Suspense>
  );
}
