import type { DemoRequest } from "@/lib/api/types";
import { isEmail } from "@/lib/validation";
import { LANDING_TEXT } from "./strings";

export interface DemoDraft {
  name: string;
  email: string;
  organization: string;
  message: string;
}

export type DemoProblems = Partial<Record<keyof DemoDraft, string>>;

export const EMPTY_DEMO: DemoDraft = { name: "", email: "", organization: "", message: "" };

export function demoProblems(draft: DemoDraft): DemoProblems {
  const problems: DemoProblems = {};
  if (!draft.name.trim()) problems.name = LANDING_TEXT.form.required;
  if (!isEmail(draft.email)) problems.email = LANDING_TEXT.form.invalidEmail;
  if (!draft.organization.trim()) problems.organization = LANDING_TEXT.form.required;
  return problems;
}

export function toDemoRequest(draft: DemoDraft): DemoRequest {
  return {
    name: draft.name.trim(),
    email: draft.email.trim(),
    organization: draft.organization.trim(),
    message: draft.message.trim() || null,
  };
}
