"use client";

import { useState } from "react";
import { Chevron } from "@/components/ui/Chevron";
import { Table, Td, Th, Tr } from "@/components/ui/Table";
import type { PracticeSpend, SpendFigures } from "@/lib/api/types";
import { PLAN_LABELS } from "@/lib/labels";
import { formatCount, formatMoney, formatUnitCost, formatWholeDollars } from "@/lib/format";
import { HQ_TEXT } from "../strings";

const words = HQ_TEXT.spend;
const NUMBER_CELL = "text-right whitespace-nowrap tabular-nums";

function FigureCells({ figures }: { figures: SpendFigures }) {
  return (
    <>
      <Td className={NUMBER_CELL}>{formatCount(figures.notes)}</Td>
      <Td className={NUMBER_CELL}>{formatCount(figures.analyses)}</Td>
      <Td className={NUMBER_CELL}>{formatCount(figures.input_tokens)}</Td>
      <Td className={NUMBER_CELL}>{formatCount(figures.output_tokens)}</Td>
      <Td className={`${NUMBER_CELL} font-medium`}>{formatMoney(figures.cost_usd)}</Td>
      <Td className={NUMBER_CELL}>{formatUnitCost(figures.cost_per_note_usd)}</Td>
      <Td className={NUMBER_CELL}>{formatCount(figures.unpriced_analyses)}</Td>
    </>
  );
}

function PlanCell({ practice }: { practice: PracticeSpend }) {
  return (
    <Td>
      <span className="block">{PLAN_LABELS[practice.plan]}</span>
      {practice.plan_monthly_cents === null ? null : (
        <span className="block text-footnote text-secondary tabular-nums">
          {words.perProvider(formatWholeDollars(practice.plan_monthly_cents))}
        </span>
      )}
    </Td>
  );
}

function PracticeRows({ practice }: { practice: PracticeSpend }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Tr>
        <Td>
          <button
            type="button"
            aria-expanded={open}
            onClick={() => setOpen((shown) => !shown)}
            className="inline-flex cursor-pointer items-center gap-2 border-0 bg-transparent p-0 text-left font-medium text-label"
          >
            <Chevron direction={open ? "down" : "right"} />
            {practice.name}
          </button>
        </Td>
        <PlanCell practice={practice} />
        <FigureCells figures={practice} />
      </Tr>
      {open
        ? practice.providers.map((provider) => (
            <Tr key={provider.id}>
              <Td>
                <span className="block pl-5 text-secondary">{provider.name}</span>
              </Td>
              <Td />
              <FigureCells figures={provider} />
            </Tr>
          ))
        : null}
    </>
  );
}

export function SpendTable({ practices }: { practices: PracticeSpend[] }) {
  const columns = words.columns;
  return (
    <Table label={words.tableLabel} minWidth="lg">
      <thead>
        <tr>
          <Th>{columns.practice}</Th>
          <Th>{columns.plan}</Th>
          <Th className="text-right">{columns.notes}</Th>
          <Th className="text-right">{columns.analyses}</Th>
          <Th className="text-right">{columns.input}</Th>
          <Th className="text-right">{columns.output}</Th>
          <Th className="text-right">{columns.cost}</Th>
          <Th className="text-right">{columns.perNote}</Th>
          <Th className="text-right">{columns.unpriced}</Th>
        </tr>
      </thead>
      <tbody>
        {practices.map((practice) => (
          <PracticeRows key={practice.id} practice={practice} />
        ))}
      </tbody>
    </Table>
  );
}
