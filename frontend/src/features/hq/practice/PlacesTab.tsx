import { EmptyState } from "@/components/ui/EmptyState";
import { Panel } from "@/components/ui/Panel";
import { StatusDot } from "@/components/ui/StatusDot";
import { Table, Td, Th, Tr } from "@/components/ui/Table";
import type { HqPracticePlace } from "@/lib/api/types";
import { formatCount } from "@/lib/format";
import { HQ_TEXT } from "../strings";

const words = HQ_TEXT.practice.places;
const NUMBER_CELL = "text-right tabular-nums";

export function PlacesTab({ places }: { places: HqPracticePlace[] }) {
  const columns = words.columns;
  return (
    <Panel aria-label={words.tableLabel}>
      {places.length === 0 ? (
        <EmptyState title={words.empty} />
      ) : (
        <Table label={words.tableLabel} minWidth="md">
          <thead>
            <tr>
              <Th>{columns.code}</Th>
              <Th>{columns.name}</Th>
              <Th>{columns.status}</Th>
              <Th className="text-right">{columns.providers}</Th>
              <Th className="text-right">{columns.notes}</Th>
            </tr>
          </thead>
          <tbody>
            {places.map((place) => (
              <Tr key={place.code}>
                <Td className="tabular-nums">{place.code}</Td>
                <Td>{place.name}</Td>
                <Td>
                  <StatusDot tone={place.active ? "ok" : "neutral"}>{place.active ? words.active : words.inactive}</StatusDot>
                </Td>
                <Td className={NUMBER_CELL}>{formatCount(place.providers)}</Td>
                <Td className={NUMBER_CELL}>{formatCount(place.notes)}</Td>
              </Tr>
            ))}
          </tbody>
        </Table>
      )}
    </Panel>
  );
}
