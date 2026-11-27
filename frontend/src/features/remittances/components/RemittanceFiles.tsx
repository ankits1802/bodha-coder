import { Panel, PanelHeader } from "@/components/ui/Panel";
import { StatusDot } from "@/components/ui/StatusDot";
import { Table, Td, Th, Tr } from "@/components/ui/Table";
import { TextButton } from "@/components/ui/TextButton";
import type { RemittanceListItem } from "@/lib/api/types";
import { FORMAT_WORDS, formatCalendarDay, formatCount } from "@/lib/format";
import { STATUS_TONES, countedStatuses } from "../remittanceModel";
import { REMITTANCE_TEXT } from "../strings";

interface RemittanceFilesProps {
  files: RemittanceListItem[];
  selectedId: string | null;
  onSelect: (remittanceId: string) => void;
}

function LineCounts({ file }: { file: RemittanceListItem }) {
  return (
    <span className="flex flex-wrap gap-x-3 gap-y-1">
      {countedStatuses(file.counts).map(({ status, count }) => (
        <StatusDot key={status} tone={STATUS_TONES[status]}>
          {REMITTANCE_TEXT.statusCount(formatCount(count), REMITTANCE_TEXT.status[status])}
        </StatusDot>
      ))}
    </span>
  );
}

export function RemittanceFiles({ files, selectedId, onSelect }: RemittanceFilesProps) {
  const words = REMITTANCE_TEXT.fileColumns;
  return (
    <Panel>
      <PanelHeader title={REMITTANCE_TEXT.filesTitle} />
      <Table label={REMITTANCE_TEXT.filesLabel} minWidth="lg">
        <thead>
          <tr>
            <Th>{words.file}</Th>
            <Th>{words.payer}</Th>
            <Th>{words.paidOn}</Th>
            <Th>{words.lines}</Th>
            <Th>{words.appealBy}</Th>
          </tr>
        </thead>
        <tbody>
          {files.map((file) => (
            <Tr key={file.id} selected={file.id === selectedId}>
              <Td>
                <TextButton aria-current={file.id === selectedId ? "true" : undefined} onClick={() => onSelect(file.id)}>
                  {file.file_name}
                </TextButton>
              </Td>
              <Td className="text-secondary">{file.payer ?? FORMAT_WORDS.empty}</Td>
              <Td className="text-secondary tabular-nums">{file.paid_on ? formatCalendarDay(file.paid_on, "year") : FORMAT_WORDS.empty}</Td>
              <Td>
                <LineCounts file={file} />
              </Td>
              <Td className="text-secondary tabular-nums">
                {file.next_appeal_by ? formatCalendarDay(file.next_appeal_by, "year") : FORMAT_WORDS.empty}
              </Td>
            </Tr>
          ))}
        </tbody>
      </Table>
    </Panel>
  );
}
