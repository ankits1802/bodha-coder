import { describe, expect, it } from "vitest";
import { draftFrom, hasProblems, problemsOf, scopesOf, settingsFrom, withNoteType } from "../ehrForm";
import { DEFAULT_SCOPES, PULLING, WITH_KEY } from "./ehrFixtures";

describe("EHR connection form", () => {
  it("starts from the default scopes and progress notes", () => {
    const draft = draftFrom(WITH_KEY);
    expect(draft).toEqual({ baseUrl: "", clientId: "", scopes: DEFAULT_SCOPES.join("\n"), noteTypes: ["progress"], startDate: null });
  });

  it("reads scopes separated by spaces or lines, once each", () => {
    expect(scopesOf("system/Encounter.read  system/Binary.read\nsystem/Encounter.read\n")).toEqual([
      "system/Encounter.read",
      "system/Binary.read",
    ]);
  });

  it("keeps note types in the catalog order", () => {
    const draft = { ...draftFrom(WITH_KEY), noteTypes: ["nursing_facility"] as const };
    expect(withNoteType(draft, "progress", true)).toEqual(["progress", "nursing_facility"]);
    expect(withNoteType(draft, "nursing_facility", false)).toEqual([]);
  });

  it("names every missing field and sends a saved connection back unchanged", () => {
    const problems = problemsOf({ ...draftFrom(WITH_KEY), baseUrl: "ftp://ehr.example.com", scopes: " " });
    expect(problems).toEqual({
      baseUrl: "Enter an https address",
      clientId: "Enter the client ID",
      scopes: "Add at least one scope",
      noteTypes: null,
      startDate: "Choose a start date",
    });
    const saved = draftFrom(PULLING);
    expect(hasProblems(problemsOf(saved))).toBe(false);
    expect(settingsFrom(saved)).toEqual({
      base_url: "https://ehr.example.com/fhir/r4",
      client_id: "bodha-lakeside",
      scopes: DEFAULT_SCOPES,
      note_types: ["progress", "nursing_facility"],
      start_date: "2026-11-01",
    });
  });
});
