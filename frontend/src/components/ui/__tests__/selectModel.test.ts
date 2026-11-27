import { describe, expect, it } from "vitest";
import { allIndexes, edgeOption, matchingIndexes, optionRuns, stepOption, typeaheadOption, type SelectOption } from "../select/selectModel";

const OPTIONS: SelectOption[] = [
  { value: "", label: "Anyone" },
  { value: "u1", label: "Priya Nair" },
  { value: "u2", label: "Omar Haddad", disabled: true },
  { value: "u3", label: "Pat Owens" },
  { value: "u4", label: "Sam Okafor" },
];
const ALL = allIndexes(OPTIONS);

describe("select option movement", () => {
  it("steps over disabled options and stops at the ends", () => {
    expect(stepOption(OPTIONS, ALL, 1, 1)).toBe(3);
    expect(stepOption(OPTIONS, ALL, 3, -1)).toBe(1);
    expect(stepOption(OPTIONS, ALL, 4, 1)).toBe(4);
    expect(stepOption(OPTIONS, ALL, 0, -1)).toBe(0);
    expect(stepOption(OPTIONS, ALL, 0, 10)).toBe(4);
  });

  it("starts from the first or last usable option when nothing is active", () => {
    expect(stepOption(OPTIONS, ALL, -1, 1)).toBe(0);
    expect(stepOption(OPTIONS, ALL, -1, -1)).toBe(4);
    expect(edgeOption(OPTIONS, [2, 3, 4], "first")).toBe(3);
    expect(edgeOption(OPTIONS, [0, 1, 2], "last")).toBe(1);
    expect(edgeOption(OPTIONS, [2], "first")).toBe(-1);
  });
});

describe("select type-ahead", () => {
  it("cycles through labels starting with a repeated letter", () => {
    expect(typeaheadOption(OPTIONS, ALL, 0, "p")).toBe(1);
    expect(typeaheadOption(OPTIONS, ALL, 1, "p")).toBe(3);
    expect(typeaheadOption(OPTIONS, ALL, 3, "pp")).toBe(1);
  });

  it("matches a longer prefix from the active option onwards and skips disabled ones", () => {
    expect(typeaheadOption(OPTIONS, ALL, 1, "pa")).toBe(3);
    expect(typeaheadOption(OPTIONS, ALL, 0, "om")).toBe(-1);
    expect(typeaheadOption(OPTIONS, ALL, 0, "sam")).toBe(4);
  });
});

describe("select search and groups", () => {
  it("filters by any part of the label, ignoring case", () => {
    expect(matchingIndexes(OPTIONS, "OKA")).toEqual([4]);
    expect(matchingIndexes(OPTIONS, " a ")).toEqual([0, 1, 2, 3, 4]);
    expect(matchingIndexes(OPTIONS, "zz")).toEqual([]);
  });

  it("groups consecutive options that share a group", () => {
    const grouped: SelectOption[] = [
      { value: "a", label: "A", group: "Recent" },
      { value: "b", label: "B", group: "Recent" },
      { value: "c", label: "C", group: "All" },
      { value: "d", label: "D" },
    ];
    expect(optionRuns(grouped, [0, 1, 2, 3])).toEqual([
      { group: "Recent", indexes: [0, 1] },
      { group: "All", indexes: [2] },
      { group: undefined, indexes: [3] },
    ]);
  });
});
