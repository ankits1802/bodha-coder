import type { Role } from "@/lib/api/types";
import { canDo, canUse } from "@/lib/roles";
import type { HelpSectionKey } from "./strings";

const SECTION_ORDER: readonly HelpSectionKey[] = ["upload", "review", "ask", "compliance", "billing", "security", "shortcuts"];

const VISIBLE: Record<HelpSectionKey, (role: Role) => boolean> = {
  upload: (role) => canUse(role, "upload"),
  review: (role) => canUse(role, "queue"),
  ask: (role) => canDo(role, "ask"),
  compliance: (role) => canUse(role, "compliance"),
  billing: (role) => canUse(role, "billing"),
  security: () => true,
  shortcuts: () => true,
};

export function helpSectionsFor(role: Role): HelpSectionKey[] {
  return SECTION_ORDER.filter((key) => VISIBLE[key](role));
}
