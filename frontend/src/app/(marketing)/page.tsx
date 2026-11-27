import { LandingPage } from "@/features/landing/LandingPage";
import { loadPlanCatalog } from "@/lib/api/planCatalogServer";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  return <LandingPage catalog={await loadPlanCatalog()} />;
}
