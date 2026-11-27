import { ACCOUNT_PATH, SECURITY_SETTINGS_PATH } from "@/lib/paths";
import { canReach, type SessionUser } from "@/lib/roles";

export function securityDestination(user: SessionUser, search: string): string {
  if (!canReach(user, "security")) return ACCOUNT_PATH;
  return search ? `${SECURITY_SETTINGS_PATH}?${search}` : SECURITY_SETTINGS_PATH;
}
