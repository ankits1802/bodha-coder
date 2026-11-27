import { EmptyState } from "@/components/ui/EmptyState";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { Table, Td, Th, Tr } from "@/components/ui/Table";
import type { PersonProductivity } from "@/lib/api/types";
import { formatCount, formatMinutes, formatPercent, ratio } from "@/lib/format";
import { INSIGHTS_TEXT } from "../strings";

export function PeopleTable({ people }: { people: PersonProductivity[] }) {
  const words = INSIGHTS_TEXT.peopleColumns;
  return (
    <Panel>
      <PanelHeader title={INSIGHTS_TEXT.peopleTitle} />
      {people.length === 0 ? (
        <EmptyState title={INSIGHTS_TEXT.noPeople} />
      ) : (
        <Table label={INSIGHTS_TEXT.peopleLabel} minWidth="md">
          <thead>
            <tr>
              <Th>{words.person}</Th>
              <Th className="text-right">{words.approved}</Th>
              <Th className="text-right">{words.median}</Th>
              <Th className="text-right">{words.changed}</Th>
            </tr>
          </thead>
          <tbody>
            {people.map((person) => (
              <Tr key={person.id}>
                <Td className="font-medium">{person.name}</Td>
                <Td className="text-right tabular-nums">{formatCount(person.approved)}</Td>
                <Td className="text-right tabular-nums">{formatMinutes(person.median_minutes)}</Td>
                <Td className="text-right tabular-nums">{formatPercent(ratio(person.changed, person.approved))}</Td>
              </Tr>
            ))}
          </tbody>
        </Table>
      )}
    </Panel>
  );
}
