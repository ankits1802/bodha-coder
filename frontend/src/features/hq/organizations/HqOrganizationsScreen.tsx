"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { PageHeader } from "@/components/ui/PageHeader";
import { Panel } from "@/components/ui/Panel";
import { RemoteView } from "@/components/ui/RemoteView";
import { useRemote } from "@/hooks/useRemote";
import { getHqOrganizations } from "@/lib/api/hqOrganizations";
import { HQ_TEXT } from "../strings";
import { OrganizationDialog } from "./OrganizationDialog";
import { OrganizationsTable } from "./OrganizationsTable";

const words = HQ_TEXT.organizations;

export function HqOrganizationsScreen() {
  const remote = useRemote("hq-organizations", getHqOrganizations);
  const [adding, setAdding] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const list = remote.state.status === "success" ? remote.state.data : null;
  const practiceTotal = list ? list.reduce((sum, organization) => sum + organization.practices, 0) : 0;

  return (
    <>
      <PageHeader
        title={words.title}
        subtitle={list ? words.subtitle(list.length, practiceTotal) : undefined}
        actions={
          <Button
            variant="primary"
            onClick={() => {
              setNotice(null);
              setAdding(true);
            }}
          >
            {words.add}
          </Button>
        }
      />
      {notice ? <InlineAlert tone="ok">{notice}</InlineAlert> : null}
      <Panel aria-label={words.tableLabel}>
        <RemoteView
          state={remote.state}
          text={{ loading: words.loading, empty: words.empty, retry: HQ_TEXT.retry }}
          isEmpty={(data) => data.length === 0}
          onRetry={remote.reload}
        >
          {(data) => <OrganizationsTable organizations={data} />}
        </RemoteView>
      </Panel>
      {adding ? (
        <OrganizationDialog
          onClose={() => setAdding(false)}
          onSaved={(name) => {
            setAdding(false);
            setNotice(HQ_TEXT.organization.notices.saved(name));
            remote.reload();
          }}
        />
      ) : null}
    </>
  );
}
