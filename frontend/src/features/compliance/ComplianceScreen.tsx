"use client";

import { useEffect, useState } from "react";
import { AreaGuard } from "@/components/shared/AreaGuard";
import { prefetchNoteDetail } from "@/components/shared/noteDetail";
import { EmptyState } from "@/components/ui/EmptyState";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { PageHeader } from "@/components/ui/PageHeader";
import { RemoteView } from "@/components/ui/RemoteView";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { useQueryParams } from "@/hooks/useQueryParams";
import { usePlaceNames } from "@/hooks/usePlaceNames";
import { useRemote } from "@/hooks/useRemote";
import { useRememberedParams } from "@/hooks/useRememberedParams";
import type { ComplianceList, Role } from "@/lib/api/types";
import { getCompliance } from "@/lib/api/work";
import { formatCount } from "@/lib/format";
import { canDo } from "@/lib/roles";
import { useSession } from "@/lib/session/useSession";
import { CaseList } from "./components/CaseList";
import { FeaturedCase } from "./components/FeaturedCase";
import { PatternBanner } from "./components/PatternBanner";
import { COMPLIANCE_KINDS, countByKind, inKind, isComplianceKind, type ComplianceKind } from "./complianceKinds";
import { COMPLIANCE_TEXT } from "./strings";
import { DayChecksPanel } from "@/components/shared/day-checks/DayChecksPanel";

const REMOTE_TEXT = { loading: COMPLIANCE_TEXT.loading, empty: COMPLIANCE_TEXT.empty, retry: COMPLIANCE_TEXT.retry };
const REMEMBERED = ["kind"] as const;

interface BodyProps {
  data: ComplianceList;
  kind: ComplianceKind;
  decided: string[];
  canDecide: boolean;
  onDecided: (message: string, noteId: string) => void;
}

function ComplianceBody({ data, kind, decided, canDecide, onDecided }: BodyProps) {
  const placeNames = usePlaceNames();
  const rows = data.items.filter((row) => inKind(row, kind) && !decided.includes(row.id));
  const [featured, ...rest] = rows;
  const following = rest[0]?.id;

  useEffect(() => {
    if (following) prefetchNoteDetail(following);
  }, [following]);
  return (
    <>
      <PatternBanner patterns={data.patterns} total={data.items.length} />
      {featured ? (
        <FeaturedCase
          key={featured.id}
          row={featured}
          placeNames={placeNames}
          canDecide={canDecide}
          onDecided={(message) => onDecided(message, featured.id)}
        />
      ) : (
        <EmptyState title={COMPLIANCE_TEXT.emptyKind} />
      )}
      <CaseList rows={rest} placeNames={placeNames} />
    </>
  );
}

function ComplianceContent({ role }: { role: Role }) {
  const params = useQueryParams();
  const kindParam = params.get("kind");
  const kind: ComplianceKind = isComplianceKind(kindParam) ? kindParam : "all";
  const list = useRemote("compliance", getCompliance);
  const [notice, setNotice] = useState<string | null>(null);
  const [decided, setDecided] = useState<string[]>([]);
  useRememberedParams("compliance", REMEMBERED);
  const items = list.state.status === "success" ? list.state.data.items : null;
  const counts = items ? countByKind(items) : null;
  const segments = COMPLIANCE_KINDS.map((value) => ({ value, label: COMPLIANCE_TEXT.kinds[value], count: counts?.[value] }));
  const onDecided = (message: string, noteId: string) => {
    setNotice(message);
    setDecided((current) => [...current, noteId]);
    list.reload();
  };
  return (
    <>
      <PageHeader title={COMPLIANCE_TEXT.title} subtitle={items ? COMPLIANCE_TEXT.subtitle(formatCount(items.length)) : undefined} />
      <div className="self-start">
        <SegmentedControl
          label={COMPLIANCE_TEXT.kindFilter}
          value={kind}
          segments={segments}
          onChange={(value) => params.update({ kind: value === "all" ? null : value })}
        />
      </div>
      {notice ? <InlineAlert tone="ok">{notice}</InlineAlert> : null}
      <RemoteView state={list.state} text={REMOTE_TEXT} isEmpty={(data) => data.items.length === 0} onRetry={list.reload}>
        {(data) => (
          <ComplianceBody data={data} kind={kind} decided={decided} canDecide={canDo(role, "complianceDecision")} onDecided={onDecided} />
        )}
      </RemoteView>
      <DayChecksPanel />
    </>
  );
}

export function ComplianceScreen() {
  const { user } = useSession();
  return <AreaGuard area="compliance">{user ? <ComplianceContent role={user.role} /> : null}</AreaGuard>;
}
