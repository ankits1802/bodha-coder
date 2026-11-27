import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { LEGAL_SLUGS, legalPath } from "@/components/shared/legal/legalLinks";
import { LEGAL_DRAFT } from "@/features/legal/config";
import { legalDocument } from "@/features/legal/documents";
import { LegalDocument } from "@/features/legal/LegalDocument";
import { legalRobots } from "@/features/legal/metadata";

interface LegalPageProps {
  params: Promise<{ document: string }>;
}

export function generateStaticParams(): { document: string }[] {
  return LEGAL_SLUGS.map((document) => ({ document }));
}

export async function generateMetadata({ params }: LegalPageProps): Promise<Metadata> {
  const found = legalDocument((await params).document);
  if (!found) return {};
  return {
    title: found.title,
    description: found.summary,
    alternates: { canonical: legalPath(found.slug) },
    robots: legalRobots(LEGAL_DRAFT),
  };
}

export default async function LegalDocumentPage({ params }: LegalPageProps) {
  const found = legalDocument((await params).document);
  if (!found) notFound();
  return <LegalDocument document={found} draft={LEGAL_DRAFT} />;
}
