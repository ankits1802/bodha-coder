import type { StatusTone } from "../StatusDot";

export interface SelectOption<V extends string = string> {
  value: V;
  label: string;
  disabled?: boolean;
  tone?: StatusTone;
  group?: string;
}

export interface OptionRun {
  group: string | undefined;
  indexes: number[];
}

export const SEARCH_AFTER = 12;
export const PAGE_STEP = 10;

export function allIndexes(options: readonly SelectOption[]): number[] {
  return options.map((_, index) => index);
}

export function matchingIndexes(options: readonly SelectOption[], query: string): number[] {
  const needle = query.trim().toLocaleLowerCase();
  return options.flatMap((option, index) => (option.label.toLocaleLowerCase().includes(needle) ? [index] : []));
}

function usableOf(options: readonly SelectOption[], shown: readonly number[]): number[] {
  return shown.filter((index) => {
    const option = options[index];
    return option !== undefined && !option.disabled;
  });
}

export function edgeOption(options: readonly SelectOption[], shown: readonly number[], end: "first" | "last"): number {
  const usable = usableOf(options, shown);
  return (end === "first" ? usable[0] : usable[usable.length - 1]) ?? -1;
}

export function stepOption(options: readonly SelectOption[], shown: readonly number[], from: number, step: number): number {
  const usable = usableOf(options, shown);
  const at = usable.indexOf(from);
  if (at === -1) return edgeOption(options, shown, step > 0 ? "first" : "last");
  return usable[Math.min(Math.max(at + step, 0), usable.length - 1)] ?? -1;
}

export function typeaheadOption(options: readonly SelectOption[], shown: readonly number[], from: number, typed: string): number {
  const usable = usableOf(options, shown);
  const text = typed.toLocaleLowerCase();
  const cycling = [...text].every((char) => char === text.charAt(0));
  const needle = cycling ? text.charAt(0) : text;
  const at = usable.indexOf(from);
  const offset = cycling ? at + 1 : Math.max(at, 0);
  const ordered = [...usable.slice(offset), ...usable.slice(0, offset)];
  return ordered.find((index) => options[index]?.label.toLocaleLowerCase().startsWith(needle)) ?? -1;
}

export function optionRuns(options: readonly SelectOption[], shown: readonly number[]): OptionRun[] {
  const runs: OptionRun[] = [];
  for (const index of shown) {
    const group = options[index]?.group;
    const last = runs[runs.length - 1];
    if (last && last.group === group) last.indexes.push(index);
    else runs.push({ group, indexes: [index] });
  }
  return runs;
}
