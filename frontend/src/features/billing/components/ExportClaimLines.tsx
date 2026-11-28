"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import type { ButtonVariant } from "@/components/ui/buttonStyles";
import { Select } from "@/components/ui/Select";
import { useAction } from "@/hooks/useAction";
import { downloadClaimLines } from "@/lib/api/billing";
import type { ClaimLinesFormat } from "@/lib/api/types";
import { saveFile } from "@/lib/download";
import { formatCount } from "@/lib/format";
import { BILLING_TEXT } from "../strings";

const FORMATS: ClaimLinesFormat[] = ["csv", "json"];

interface ExportClaimLinesProps {
  visits: number;
  variant?: ButtonVariant;
  onExported: (notice: string) => void;
}

export function ExportClaimLines({ visits, variant = "primary", onExported }: ExportClaimLinesProps) {
  const words = BILLING_TEXT.claimLines;
  const [format, setFormat] = useState<ClaimLinesFormat>("csv");
  const download = useAction(downloadClaimLines);
  const amount = formatCount(visits);

  async function run(): Promise<void> {
    const outcome = await download.run(format);
    if (!outcome.ok) return;
    saveFile(outcome.value.blob, outcome.value.fileName ?? words.files[format]);
    onExported(BILLING_TEXT.exported(amount));
  }

  return (
    <span className="flex flex-wrap items-center gap-2">
      <Select<ClaimLinesFormat>
        variant="filter"
        label={words.format}
        value={format}
        options={FORMATS.map((value) => ({ value, label: words.formats[value] }))}
        onChange={setFormat}
      />
      <Button variant={variant} pending={download.pending} onClick={() => void run()}>
        {words.export(amount)}
      </Button>
      {download.error ? (
        <span role="alert" className="basis-full text-footnote text-bad-text">
          {download.error}
        </span>
      ) : null}
    </span>
  );
}
