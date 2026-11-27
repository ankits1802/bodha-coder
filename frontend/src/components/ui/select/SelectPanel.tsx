import type { RefObject } from "react";
import { SearchField } from "../SearchField";
import { UI_TEXT } from "../strings";
import { SelectOptionRow } from "./SelectOptionRow";
import { optionRuns, type OptionRun, type SelectOption } from "./selectModel";
import type { SelectView } from "./useSelect";

export interface ListNaming {
  "aria-label"?: string;
  "aria-labelledby"?: string;
}

interface OptionRunRowsProps<V extends string> {
  run: OptionRun;
  state: SelectView<V>;
  options: readonly SelectOption<V>[];
  value: V;
}

interface SelectPanelProps<V extends string> extends Omit<OptionRunRowsProps<V>, "run"> {
  naming: ListNaming;
  panelRef: RefObject<HTMLDivElement | null>;
  searchRef: RefObject<HTMLInputElement | null>;
}

function OptionRunRows<V extends string>({ run, state, options, value }: OptionRunRowsProps<V>) {
  const rows = run.indexes.map((index) => {
    const option = options[index];
    if (!option) return null;
    return (
      <SelectOptionRow
        key={index}
        id={state.optionId(index)}
        option={option}
        selected={option.value === value}
        active={index === state.active}
        onHover={() => state.onHover(index)}
        onChoose={() => state.choose(index)}
      />
    );
  });
  if (run.group === undefined) return <>{rows}</>;
  const groupId = `${state.listId}-group-${run.indexes[0] ?? 0}`;
  return (
    <div role="group" aria-labelledby={groupId}>
      <div id={groupId} role="presentation" className="px-3.5 pt-2 pb-1 text-caption font-medium text-secondary">
        {run.group}
      </div>
      {rows}
    </div>
  );
}

export function SelectPanel<V extends string>({ state, options, value, naming, panelRef, searchRef }: SelectPanelProps<V>) {
  const runs = optionRuns(options, state.shown);
  return (
    <div
      ref={panelRef}
      style={{ ...state.style, minWidth: state.width }}
      className="fixed z-30 flex flex-col overflow-hidden rounded-field bg-surface shadow-float"
    >
      {state.searchable ? (
        <div className="flex-none border-b border-hairline p-2">
          <SearchField
            ref={searchRef}
            label={UI_TEXT.select.search}
            className="w-full"
            role="combobox"
            autoComplete="off"
            aria-autocomplete="list"
            aria-expanded="true"
            aria-controls={state.listId}
            aria-activedescendant={state.active >= 0 ? state.optionId(state.active) : undefined}
            value={state.query}
            onChange={(event) => state.onSearch(event.target.value)}
            onKeyDown={state.onSearchKey}
          />
        </div>
      ) : null}
      <div id={state.listId} role="listbox" {...naming} className="relative min-h-0 flex-1 overflow-y-auto py-1">
        {runs.map((run) => (
          <OptionRunRows key={`${run.group ?? ""}-${run.indexes[0] ?? 0}`} run={run} state={state} options={options} value={value} />
        ))}
      </div>
      {state.shown.length === 0 ? (
        <p role="status" className="m-0 px-3.5 pb-2.5 text-subhead text-secondary">
          {UI_TEXT.select.noMatches}
        </p>
      ) : null}
    </div>
  );
}
