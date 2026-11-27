export const TIME_ZONE_LABELS: Record<string, string> = {
  "America/New_York": "Eastern (New York)",
  "America/Chicago": "Central (Chicago)",
  "America/Denver": "Mountain (Denver)",
  "America/Phoenix": "Arizona (Phoenix)",
  "America/Los_Angeles": "Pacific (Los Angeles)",
  "America/Anchorage": "Alaska (Anchorage)",
  "Pacific/Honolulu": "Hawaii (Honolulu)",
  UTC: "UTC",
};

export const DEFAULT_TIME_ZONE = "America/Chicago";
export const TIME_ZONES: readonly string[] = Object.keys(TIME_ZONE_LABELS);

export function zoneOptions(current: string): { options: readonly string[]; labels: Record<string, string> } {
  if (TIME_ZONES.includes(current)) return { options: TIME_ZONES, labels: TIME_ZONE_LABELS };
  return { options: [...TIME_ZONES, current], labels: { ...TIME_ZONE_LABELS, [current]: current } };
}

export function preferredTimeZone(detected: string | undefined = Intl.DateTimeFormat().resolvedOptions().timeZone): string {
  return detected && TIME_ZONES.includes(detected) ? detected : DEFAULT_TIME_ZONE;
}
