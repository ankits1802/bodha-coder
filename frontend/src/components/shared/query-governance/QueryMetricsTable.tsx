import { EmptyState } from "@/components/ui/EmptyState";
import { Table, Td, Th, Tr } from "@/components/ui/Table";
import type { QueryMetrics, QueryMetricsReport } from "@/lib/api/types";
import { FORMAT_WORDS, formatCount, formatMinutes, formatPercent } from "@/lib/format";
import { QUERY_TEXT } from "./strings";

const MINUTES_PER_HOUR = 60;

function MetricCells({ metrics }: { metrics: QueryMetrics }) {
  return (
    <>
      <Td className="text-right tabular-nums">{formatCount(metrics.queries)}</Td>
      <Td className="text-right tabular-nums">{metrics.per_100_notes === null ? FORMAT_WORDS.empty : formatCount(metrics.per_100_notes)}</Td>
      <Td className="text-right tabular-nums">{formatPercent(metrics.response_rate)}</Td>
      <Td className="text-right tabular-nums">
        {formatMinutes(metrics.median_hours === null ? null : metrics.median_hours * MINUTES_PER_HOUR)}
      </Td>
      <Td className="text-right tabular-nums">{formatPercent(metrics.agree_rate)}</Td>
      <Td className="text-right tabular-nums">{formatPercent(metrics.repeat_rate)}</Td>
    </>
  );
}

export function QueryMetricsTable({ report }: { report: QueryMetricsReport }) {
  const words = QUERY_TEXT.columns;
  if (report.total.queries === 0) return <EmptyState title={QUERY_TEXT.noQueries} />;
  return (
    <Table label={QUERY_TEXT.tableLabel} minWidth="lg">
      <thead>
        <tr>
          <Th>{words.provider}</Th>
          <Th className="text-right">{words.queries}</Th>
          <Th className="text-right">{words.per100}</Th>
          <Th className="text-right">{words.responded}</Th>
          <Th className="text-right">{words.medianWait}</Th>
          <Th className="text-right">{words.agreed}</Th>
          <Th className="text-right">{words.repeated}</Th>
        </tr>
      </thead>
      <tbody>
        {report.providers.map((provider) => (
          <Tr key={provider.provider_id}>
            <Td className="font-medium">{provider.provider_name}</Td>
            <MetricCells metrics={provider} />
          </Tr>
        ))}
        <Tr>
          <Td className="font-semibold">{QUERY_TEXT.allProviders}</Td>
          <MetricCells metrics={report.total} />
        </Tr>
      </tbody>
    </Table>
  );
}
