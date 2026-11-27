import type { Metadata } from "next";
import { VerifyDomainScreen } from "@/features/verify-domain/VerifyDomainScreen";
import { VERIFY_DOMAIN_TEXT } from "@/features/verify-domain/strings";

export const metadata: Metadata = { title: VERIFY_DOMAIN_TEXT.pageTitle, robots: { index: false, follow: false } };

export default function VerifyDomainPage() {
  return <VerifyDomainScreen />;
}
