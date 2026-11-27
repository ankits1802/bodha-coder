import Link from "next/link";
import { batchCounts } from "@/components/shared/batchProgress";
import { StatusDot } from "@/components/ui/StatusDot";
import { Table, Td, Th, Tr } from "@/components/ui/Table";
import { placeName, type PlaceNames } from "@/hooks/usePlaceNames";
import type { UploadedBatch } from "@/lib/api/types";
import { formatCalendarDay, formatCount, formatDateTime } from "@/lib/format";
import { UPLOAD_TEXT } from "../strings";
import { batchQueueHref, uploadStatus } from "../uploadHistory";

interface UploadHistoryTableProps {
  batches: UploadedBatch[];
  placeNames: PlaceNames;
}

const words = UPLOAD_TEXT.history;

function HistoryRow({ batch, placeNames }: { batch: UploadedBatch; placeNames: PlaceNames }) {
  const status = uploadStatus(batch);
  const day = formatCalendarDay(batch.service_date);
  return (
    <Tr>
      <Td className="whitespace-nowrap text-secondary tabular-nums">
        <time dateTime={batch.created_at}>{formatDateTime(batch.created_at)}</time>
      </Td>
      <Td>
        <Link
          href={batchQueueHref(batch.id)}
          aria-label={words.openBatch(batch.provider_name, day)}
          className="font-medium underline-offset-2 hover:underline"
        >
          {batch.provider_name}
        </Link>
      </Td>
      <Td className="whitespace-nowrap tabular-nums">{day}</Td>
      <Td className="text-secondary">{placeName(placeNames, batch.place_code)}</Td>
      <Td className="text-secondary">{batch.uploaded_by}</Td>
      <Td className="text-right tabular-nums">{formatCount(batchCounts(batch).total)}</Td>
      <Td>
        <StatusDot tone={status.tone}>{status.label}</StatusDot>
      </Td>
    </Tr>
  );
}

export function UploadHistoryTable({ batches, placeNames }: UploadHistoryTableProps) {
  const columns = words.columns;
  return (
    <Table label={words.tableLabel} minWidth="lg">
      <thead>
        <tr>
          <Th>{columns.uploaded}</Th>
          <Th>{columns.provider}</Th>
          <Th>{columns.seen}</Th>
          <Th>{columns.place}</Th>
          <Th>{columns.by}</Th>
          <Th className="text-right">{columns.notes}</Th>
          <Th>{columns.status}</Th>
        </tr>
      </thead>
      <tbody>
        {batches.map((batch) => (
          <HistoryRow key={batch.id} batch={batch} placeNames={placeNames} />
        ))}
      </tbody>
    </Table>
  );
}
