import type { MenuItem } from "@/components/ui/MenuButton";
import { NEW_PRACTICE_PATH } from "@/lib/api/auth";
import type { PracticeChoice, User } from "@/lib/api/types";
import { ROLE_LABELS } from "@/lib/labels";
import { ACCOUNT_PATH, organizationPath, type OrganizationTab } from "@/lib/paths";
import { canReach } from "@/lib/roles";
import { PRACTICE_TEXT } from "../practices/strings";
import { SHARED_TEXT } from "../strings";
import { TOUR_TEXT } from "../tour/strings";

export interface AccountHandlers {
  open: (path: string) => void;
  switchTo: (practiceId: string) => void;
  leave: (practice: PracticeChoice) => void;
  tour: () => void;
  signOut: () => void;
}

function practiceItems(user: User, handlers: AccountHandlers): MenuItem[] {
  const current = user.practice?.id ?? null;
  const choices = user.practices.map((practice) => ({
    key: `practice-${practice.id}`,
    label: PRACTICE_TEXT.choice(practice.name, ROLE_LABELS[practice.role]),
    checked: practice.id === current,
    onSelect: () => handlers.switchTo(practice.id),
  }));
  const leaving = user.practices.map((practice) => ({
    key: `leave-${practice.id}`,
    label: PRACTICE_TEXT.leaveItem(practice.name),
    tone: "danger" as const,
    onSelect: () => handlers.leave(practice),
  }));
  return [...choices, ...leaving, { key: "newPractice", label: PRACTICE_TEXT.newPractice, onSelect: () => handlers.open(NEW_PRACTICE_PATH) }];
}

function organizationItems(user: User, handlers: AccountHandlers, tab?: OrganizationTab): MenuItem[] {
  return (user.organizations ?? []).map((organization) => ({
    key: `organization-${organization.id}`,
    label: PRACTICE_TEXT.organization(organization.name),
    onSelect: () => handlers.open(organizationPath(organization.id, tab)),
  }));
}

export function accountMenuItems(user: User, handlers: AccountHandlers): MenuItem[] {
  const signOut: MenuItem = { key: "signOut", label: SHARED_TEXT.signOut, onSelect: handlers.signOut };
  if (user.billing_only) return [...organizationItems(user, handlers, "plan"), signOut];
  const tour: MenuItem = { key: "tour", label: TOUR_TEXT.take, onSelect: handlers.tour };
  if (!canReach(user, "account")) return [tour, signOut];
  const account: MenuItem = { key: "account", label: SHARED_TEXT.account.page, onSelect: () => handlers.open(ACCOUNT_PATH) };
  return [account, ...practiceItems(user, handlers), ...organizationItems(user, handlers), tour, signOut];
}
