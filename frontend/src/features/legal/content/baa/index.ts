import { LEGAL_PARTY } from "../../config";
import type { LegalDocumentData } from "../../types";
import { LEGAL_TITLES } from "../headings";
import { BAA_CLOSING } from "./closing";
import { BAA_DUTIES } from "./duties";
import { BAA_OPENING } from "./opening";
import { BAA_SUPPORT } from "./support";

export const BAA: LegalDocumentData = {
  slug: "baa",
  title: LEGAL_TITLES.baa,
  summary: `The HIPAA terms that govern protected health information you upload to ${LEGAL_PARTY.product}.`,
  version: "1.0",
  updated: "2026-11-27",
  numbered: true,
  sections: [...BAA_OPENING, ...BAA_DUTIES, ...BAA_SUPPORT, ...BAA_CLOSING],
};
