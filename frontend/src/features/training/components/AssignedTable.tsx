import { ButtonLink } from "@/components/ui/ButtonLink";
import { StatusDot } from "@/components/ui/StatusDot";
import { Table, Td, Th, Tr } from "@/components/ui/Table";
import type { AssignedSample } from "@/lib/api/types";
import { formatInstantDay } from "@/lib/format";
import { TRAINING_TEXT } from "../strings";

function hrefFor(sample: AssignedSample): string {
  const id = encodeURIComponent(sample.id);
  return sample.purpose === "audit" ? `/quality/review/${id}` : `/training/${id}`;
}

export function AssignedTable({ samples }: { samples: AssignedSample[] }) {
  const words = TRAINING_TEXT.columns;
  return (
    <Table label={TRAINING_TEXT.assignedLabel} minWidth="md">
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
          const kind = TRAINING_TEXT.purposes[sample.purpose];
          const day = formatInstantDay(sample.started_at);
          return (
            <Tr key={sample.id}>
              <Td className="font-medium">{kind}</Td>
              <Td className="tabular-nums">{day}</Td>
              <Td className="text-right tabular-nums">{TRAINING_TEXT.progress(sample.done, sample.total)}</Td>
              <Td className="text-right">
                {sample.done < sample.total ? (
                  <ButtonLink href={hrefFor(sample)} size="sm" aria-label={TRAINING_TEXT.codeLabel(kind, day)}>
                    {TRAINING_TEXT.code}
                  </ButtonLink>
                ) : (
                  <StatusDot tone="ok">{TRAINING_TEXT.finished}</StatusDot>
                )}
              </Td>
            </Tr>
          );
        })}
      </tbody>
    </Table>
  );
}
