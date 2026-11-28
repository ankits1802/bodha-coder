"use client";

import { useRemote, type Remote } from "@/hooks/useRemote";
import { getOrganization, getOrganizationInsights, getOrganizationPlan } from "@/lib/api/organizations";
import type { InsightDays, OrganizationInsights, OrganizationOverview, OrganizationPlan } from "@/lib/api/types";

export const DEFAULT_DAYS: InsightDays = 30;

export function organizationKey(organizationId: string): string {
  return `organization:${organizationId}`;
}

export function organizationPlanKey(organizationId: string): string {
  return `organization-plan:${organizationId}`;
}

export function organizationInsightsKey(organizationId: string, days: InsightDays): string {
  return `organization-insights:${organizationId}:${days}`;
}

export function useOrganization(organizationId: string): Remote<OrganizationOverview> {
  return useRemote(organizationKey(organizationId), () => getOrganization(organizationId));
}

export function useOrganizationPlan(organizationId: string): Remote<OrganizationPlan> {
  return useRemote(organizationPlanKey(organizationId), () => getOrganizationPlan(organizationId));
}

export function useOrganizationInsights(organizationId: string, days: InsightDays): Remote<OrganizationInsights> {
  return useRemote(organizationInsightsKey(organizationId, days), () => getOrganizationInsights(organizationId, days));
}
