import type { StatusTone } from "@/components/ui/StatusDot";
import type { HqOrganization, OrganizationStatus } from "@/lib/api/types";
import { isoDateInZone } from "@/lib/dates";
import { formatCalendarDay } from "@/lib/format";
import { HQ_TEXT } from "./strings";

export const ORGANIZATION_TIME_ZONE = "UTC";

const TONES: Record<OrganizationStatus, StatusTone> = { active: "ok", closed: "neutral", purged: "neutral" };

type OrganizationDates = Pick<HqOrganization, "status" | "renews_on" | "purge_after" | "purged_at">;

export function organizationToday(now: Date = new Date()): string {
  return isoDateInZone(now, ORGANIZATION_TIME_ZONE);
}

export function organizationStatusView(organization: Pick<HqOrganization, "status">): { tone: StatusTone; label: string } {
  return { tone: TONES[organization.status], label: HQ_TEXT.organizations.statuses[organization.status] };
}

export function organizationRenewal(organization: OrganizationDates, today: string = organizationToday()): string {
  const words = HQ_TEXT.status;
  if (organization.status === "purged") {
    return words.purged(organization.purged_at ? formatCalendarDay(organization.purged_at.slice(0, 10), "year") : "").trim();
  }
  if (organization.status === "closed" && organization.purge_after) return words.purgeAfter(formatCalendarDay(organization.purge_after, "year"));
  if (!organization.renews_on) return words.noRenewal;
  const day = formatCalendarDay(organization.renews_on, "year");
  return organization.renews_on < today ? words.ended(day) : words.renews(day);
}

export function canCloseOrganization(organization: Pick<HqOrganization, "status">): boolean {
  return organization.status === "active";
}

export function canPurgeOrganization(organization: OrganizationDates, today: string = organizationToday()): boolean {
  return organization.status === "closed" && organization.purge_after !== null && today >= organization.purge_after;
}
