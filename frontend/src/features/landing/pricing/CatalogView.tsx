"use client";

import type { ReactNode } from "react";
import { RemoteView } from "@/components/ui/RemoteView";
import { usePlanCatalog } from "@/hooks/usePlanCatalog";
import type { PlanCatalog } from "@/lib/api/types";
import { PRICING_TEXT } from "./strings";

type RenderCatalog = (catalog: PlanCatalog) => ReactNode;

const TEXT = { loading: PRICING_TEXT.loading, empty: PRICING_TEXT.loading, retry: PRICING_TEXT.retry };

function FetchedCatalog({ children }: { children: RenderCatalog }) {
  const catalog = usePlanCatalog();
  return (
    <RemoteView state={catalog.state} text={TEXT} onRetry={catalog.reload}>
      {children}
    </RemoteView>
  );
}

export function CatalogView({ catalog, children }: { catalog: PlanCatalog | null; children: RenderCatalog }) {
  return catalog ? children(catalog) : <FetchedCatalog>{children}</FetchedCatalog>;
}
