import { LEGAL_PARTY } from "../../config";
import type { LegalDocumentData } from "../../types";
import { LEGAL_TITLES } from "../headings";
import { TERMS_DATA } from "./data";
import { TERMS_DUTIES } from "./duties";
import { TERMS_ENDING } from "./ending";
import { TERMS_GENERAL } from "./general";
import { TERMS_MONEY } from "./money";
import { TERMS_OPENING } from "./opening";
import { TERMS_RIGHTS } from "./rights";
import { TERMS_RISK } from "./risk";

export const TERMS: LegalDocumentData = {
  slug: "terms",
  title: LEGAL_TITLES.terms,
  summary: `The agreement between your organization and us for using ${LEGAL_PARTY.product}.`,
  version: "1.0",
  updated: "2026-11-27",
  numbered: true,
  sections: [...TERMS_OPENING, ...TERMS_DUTIES, ...TERMS_MONEY, ...TERMS_DATA, ...TERMS_RIGHTS, ...TERMS_ENDING, ...TERMS_RISK, ...TERMS_GENERAL],
};
