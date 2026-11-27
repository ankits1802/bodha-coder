import { ButtonLink } from "@/components/ui/ButtonLink";
import { StatusDot } from "@/components/ui/StatusDot";
import { Table, Td, Th, Tr } from "@/components/ui/Table";
import type { AssignedSample } from "@/lib/api/types";
import { formatInstantDay } from "@/lib/format";
import { ASSIGNED_TEXT } from "./strings";

function assignedHref(sample: Pick<AssignedSample, "id" | "purpose">): string {
  const id = encodeURIComponent(sample.id);
  return sample.purpose === "audit" ? `/insights/quality/review/${id}` : `/training/${id}`;
}

export function AssignedTable({ samples }: { samples: AssignedSample[] }) {
  const words = ASSIGNED_TEXT.columns;
  return (
    <Table label={ASSIGNED_TEXT.tableLabel} minWidth="md">
      <thead>
        <tr>
          <Th>{words.kind}</Th>
          <Th>{words.started}</Th>
          <Th className="text-right">{words.progress}</Th>
          <Th>
            <span className="sr-only">{words.action}</span>
          </Th>
        </tr>
      </thead>
      <tbody>
        {samples.map((sample) => {
          const kind = ASSIGNED_TEXT.purposes[sample.purpose];
          const day = formatInstantDay(sample.started_at);
          return (
            <Tr key={sample.id}>
              <Td className="font-medium">{kind}</Td>
              <Td className="tabular-nums">{day}</Td>
              <Td className="text-right tabular-nums">{ASSIGNED_TEXT.progress(sample.done, sample.total)}</Td>
              <Td className="text-right">
                {sample.done < sample.total ? (
                  <ButtonLink href={assignedHref(sample)} size="sm" aria-label={ASSIGNED_TEXT.codeLabel(kind, day)}>
                    {ASSIGNED_TEXT.code}
                  </ButtonLink>
                ) : (
                  <StatusDot tone="ok">{ASSIGNED_TEXT.finished}</StatusDot>
                )}
              </Td>
            </Tr>
          );
        })}
      </tbody>
    </Table>
  );
}
