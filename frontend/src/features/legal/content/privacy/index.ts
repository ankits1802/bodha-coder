import { LEGAL_PARTY } from "../../config";
import type { LegalDocumentData } from "../../types";
import { LEGAL_TITLES } from "../headings";
import { PRIVACY_COLLECT } from "./collect";
import { PRIVACY_RIGHTS } from "./rights";
import { PRIVACY_SHARE } from "./share";
import { PRIVACY_USE } from "./use";

export const PRIVACY: LegalDocumentData = {
  slug: "privacy",
  title: LEGAL_TITLES.privacy,
  summary: `How we handle personal information about website visitors and ${LEGAL_PARTY.product} account users.`,
  version: "1.3",
  updated: "2026-11-28",
  numbered: true,
  sections: [...PRIVACY_COLLECT, ...PRIVACY_USE, ...PRIVACY_SHARE, ...PRIVACY_RIGHTS],
};
