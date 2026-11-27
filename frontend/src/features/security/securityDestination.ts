import { ACCESS_LOG_PATH, ACCOUNT_PATH, SECURITY_SETTINGS_PATH } from "@/lib/paths";
import { canReach, type SessionUser } from "@/lib/roles";

export function securityDestination(user: SessionUser, search: string): string {
  if (search && canReach(user, "accessLog")) return `${ACCESS_LOG_PATH}?${search}`;
  if (canReach(user, "security")) return SECURITY_SETTINGS_PATH;
  return canReach(user, "accessLog") ? ACCESS_LOG_PATH : ACCOUNT_PATH;
}
