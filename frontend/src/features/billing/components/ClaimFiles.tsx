"use client";

import { useState } from "react";
import { SHARED_TEXT } from "@/components/shared/strings";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Pager } from "@/components/ui/Pager";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { RemoteView } from "@/components/ui/RemoteView";
import { useAction } from "@/hooks/useAction";
import { useRemote } from "@/hooks/useRemote";
import { downloadStoredClaimFile, getClaimFiles } from "@/lib/api/claims";
import type { ClaimFileRecord } from "@/lib/api/types";
import { saveFile } from "@/lib/download";
import { CLAIM_FILE_TEXT } from "../strings";
import { AckUploadButton } from "./AckUploadButton";
import { ClaimFileItem } from "./ClaimFileItem";

const REMOTE_TEXT = { loading: CLAIM_FILE_TEXT.loading, empty: CLAIM_FILE_TEXT.empty, retry: CLAIM_FILE_TEXT.retry };

export function ClaimFiles({ refresh }: { refresh: number }) {
  const [offset, setOffset] = useState(0);
  const files = useRemote(`claim-files:${offset}:${refresh}`, () => getClaimFiles(offset));
  const download = useAction(downloadStoredClaimFile);
  const [notice, setNotice] = useState<string | null>(null);

  async function save(record: ClaimFileRecord): Promise<void> {
    const outcome = await download.run(record.id);
    if (outcome.ok) saveFile(outcome.value.blob, outcome.value.fileName ?? record.file_name);
  }

  return (
    <Panel aria-label={CLAIM_FILE_TEXT.title}>
      <PanelHeader
        title={CLAIM_FILE_TEXT.title}
        actions={
          <AckUploadButton
            onUploaded={(message) => {
              setNotice(message);
              files.reload();
            }}
          />
        }
      />
      {notice ? (
        <div className="px-4 pb-3">
          <InlineAlert tone="ok">{notice}</InlineAlert>
        </div>
      ) : null}
      <RemoteView state={files.state} text={REMOTE_TEXT} isEmpty={(data) => data.items.length === 0 && data.offset === 0} onRetry={files.reload}>
        {(data) => (
          <>
            <ul className="m-0 list-none p-0">
              {data.items.map((record) => (
                <ClaimFileItem key={record.id} record={record} onDownload={(chosen) => void save(chosen)} />
              ))}
            </ul>
            <div className="px-4 pb-3">
              <Pager
                offset={data.offset}
                pageSize={data.page_size}
                shown={data.items.length}
                total={data.total}
                text={SHARED_TEXT.pager}
                onOffset={setOffset}
              />
            </div>
          </>
        )}
      </RemoteView>
      {download.error ? (
        <p role="alert" className="m-0 px-4 pb-3 text-footnote text-bad-text">
          {download.error}
        </p>
      ) : null}
    </Panel>
  );
}
