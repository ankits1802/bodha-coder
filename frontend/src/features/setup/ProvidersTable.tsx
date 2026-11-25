import { Button } from "@/components/ui/Button";
import { Table, Td, Th, Tr } from "@/components/ui/Table";
import { TextButton } from "@/components/ui/TextButton";
import type { Provider } from "@/lib/api/types";
import { FORMAT_WORDS } from "@/lib/format";
import { CHANNEL_LABELS } from "@/lib/labels";
import { PROVIDER_TEXT } from "./strings";

interface ProvidersTableProps {
  providers: Provider[];
  placeNames: Map<string, string>;
  onEdit: (provider: Provider) => void;
}

function placeOf(code: string | null, placeNames: Map<string, string>): string {
  if (!code) return FORMAT_WORDS.empty;
  return placeNames.get(code) ?? code;
}

export function ProvidersTable({ providers, placeNames, onEdit }: ProvidersTableProps) {
  const columns = PROVIDER_TEXT.columns;
  return (
    <Table label={PROVIDER_TEXT.tableLabel} minWidth="md">
      <thead>
        <tr>
          <Th>{columns.name}</Th>
          <Th>{columns.specialty}</Th>
          <Th>{columns.npi}</Th>
          <Th>{columns.place}</Th>
          <Th>{columns.channel}</Th>
          <Th>
            <span className="sr-only">{columns.edit}</span>
          </Th>
        </tr>
      </thead>
      <tbody>
        {providers.map((provider) => (
          <Tr key={provider.id}>
            <Td className="font-medium">
              {provider.name}
              <span className="ml-1.5 rounded-chip bg-chip px-1.5 py-px text-micro font-semibold text-label-soft">
                {provider.credential}
              </span>
              {provider.active ? null : <span className="ml-2 text-footnote text-tertiary">{PROVIDER_TEXT.inactive}</span>}
            </Td>
            <Td className="text-secondary">{provider.specialty ?? FORMAT_WORDS.empty}</Td>
            <Td className="tabular-nums">
              {provider.npi ?? (
                <TextButton tone="warn" onClick={() => onEdit(provider)}>
                  {PROVIDER_TEXT.addNpi}
                </TextButton>
              )}
            </Td>
            <Td className="text-secondary">{placeOf(provider.place_code, placeNames)}</Td>
            <Td className="text-secondary">{CHANNEL_LABELS[provider.channel]}</Td>
            <Td className="text-right">
              <Button variant="plain" size="sm" aria-label={PROVIDER_TEXT.editFor(provider.name)} onClick={() => onEdit(provider)}>
                {columns.edit}
              </Button>
            </Td>
          </Tr>
        ))}
      </tbody>
    </Table>
  );
}
