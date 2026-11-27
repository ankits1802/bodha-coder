"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { MenuButton, type MenuItem } from "@/components/ui/MenuButton";
import { PageHeader } from "@/components/ui/PageHeader";
import { RemoteView } from "@/components/ui/RemoteView";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { StatusDot } from "@/components/ui/StatusDot";
import { useQueryParams } from "@/hooks/useQueryParams";
import { useRemote } from "@/hooks/useRemote";
import { getHqOrganizationPage } from "@/lib/api/hqOrganizations";
import type { HqOrganization, HqOrganizationPage } from "@/lib/api/types";
import { canCloseOrganization, canPurgeOrganization, organizationStatusView } from "../organizationStatus";
import { SpendTab } from "../practice/SpendTab";
import { HQ_TEXT } from "../strings";
import { AdminsTab } from "./AdminsTab";
import { OrganizationDialogs, type OrganizationDialogKind } from "./OrganizationDialogs";
import { OrganizationPlanTab } from "./OrganizationPlanTab";
import { ORGANIZATION_TABS, organizationTabFrom, type OrganizationTab } from "./organizationTabs";
import { PracticesTab } from "./PracticesTab";

const words = HQ_TEXT.organization;
const SEGMENTS = ORGANIZATION_TABS.map((value) => ({ value, label: words.tabs[value] }));

interface TabBodyProps {
  tab: OrganizationTab;
  page: HqOrganizationPage;
  onChanged: (notice: string | null) => void;
}

function TabBody({ tab, page, onChanged }: TabBodyProps) {
  const organization = page.organization;
  if (tab === "admins") return <AdminsTab organization={organization} admins={page.admins} onChanged={onChanged} />;
  if (tab === "plan") return <OrganizationPlanTab organization={organization} plan={page.plan} />;
  if (tab === "spend") return <SpendTab scope={{ organization_id: organization.id }} />;
  return <PracticesTab organization={organization} practices={page.practices} onChanged={onChanged} />;
}

function menuItems(organization: HqOrganization, open: (kind: OrganizationDialogKind) => void): MenuItem[] {
  const items: MenuItem[] = [];
  if (canCloseOrganization(organization)) items.push({ key: "close", label: words.menu.close, tone: "danger", onSelect: () => open("close") });
  if (canPurgeOrganization(organization)) items.push({ key: "purge", label: words.menu.purge, tone: "danger", onSelect: () => open("purge") });
  return items;
}

function HeaderActions({ organization, onOpen }: { organization: HqOrganization; onOpen: (kind: OrganizationDialogKind) => void }) {
  const items = menuItems(organization, onOpen);
  const active = organization.status === "active";
  return (
    <>
      {active ? <Button onClick={() => onOpen("edit")}>{words.edit}</Button> : null}
      {active ? (
        <Button variant="primary" onClick={() => onOpen("renew")}>
          {words.renew}
        </Button>
      ) : null}
      {items.length > 0 ? <MenuButton label={words.moreFor(organization.name)} items={items} /> : null}
    </>
  );
}

export function HqOrganizationScreen({ organizationId }: { organizationId: string }) {
  const remote = useRemote(`hq-organization:${organizationId}`, () => getHqOrganizationPage(organizationId));
  const query = useQueryParams();
  const tab = organizationTabFrom(query.get("tab"));
  const [dialog, setDialog] = useState<OrganizationDialogKind | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const organization = remote.state.status === "success" ? remote.state.data.organization : null;
  const status = organization ? organizationStatusView(organization) : null;

  function open(kind: OrganizationDialogKind): void {
    setNotice(null);
    setDialog(kind);
  }

  function changed(message: string | null): void {
    setDialog(null);
    setNotice(message);
    remote.reload();
  }

  return (
    <>
      <PageHeader
        title={organization?.name ?? words.title}
        subtitle={status ? <StatusDot tone={status.tone}>{status.label}</StatusDot> : undefined}
        actions={organization ? <HeaderActions organization={organization} onOpen={open} /> : null}
      />
      {notice ? <InlineAlert tone="ok">{notice}</InlineAlert> : null}
      <SegmentedControl<OrganizationTab>
        label={words.tabsLabel}
        value={tab}
        segments={SEGMENTS}
        onChange={(next) => query.update({ tab: next, from: null, to: null })}
      />
      <RemoteView state={remote.state} text={{ loading: words.loading, empty: words.loading, retry: HQ_TEXT.retry }} onRetry={remote.reload}>
        {(data) => <TabBody tab={tab} page={data} onChanged={changed} />}
      </RemoteView>
      {organization && dialog ? <OrganizationDialogs kind={dialog} organization={organization} onDone={changed} onClose={() => setDialog(null)} /> : null}
    </>
  );
}
