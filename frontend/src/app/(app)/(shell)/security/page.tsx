import { Suspense } from "react";
import { SecurityRedirect } from "@/features/security/SecurityRedirect";

export default function SecurityPage() {
  return (
    <Suspense>
      <SecurityRedirect />
    </Suspense>
  );
}
