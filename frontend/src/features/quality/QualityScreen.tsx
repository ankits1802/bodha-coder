"use client";

import type { ReactNode } from "react";
import { AreaGuard } from "@/components/shared/AreaGuard";
import { PageHeader } from "@/components/ui/PageHeader";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { useQueryParams } from "@/hooks/useQueryParams";
import { useSession } from "@/lib/session/useSession";
import { AuditsView } from "./components/AuditsView";
import { AutonomyView } from "./components/AutonomyView";
import { EvaluationView } from "./components/EvaluationView";
import { SampleResultsView } from "./components/SampleResultsView";
import { TrainingView } from "./components/TrainingView";
import { isQualityAdmin, parseView, viewsFor, type QualityView } from "./qualityModel";
import { QUALITY_TEXT } from "./strings";

function QualityContent() {
  const { user } = useSession();
  const params = useQueryParams();
  const view = parseView(params.get("view"), user?.role);
  const sample = params.get("sample");
  const admin = isQualityAdmin(user?.role);
  const views: Record<QualityView, ReactNode> = {
    audits: sample ? <SampleResultsView key={sample} sampleId={sample} /> : <AuditsView />,
    training: <TrainingView />,
    evaluation: <EvaluationView canRun={admin} />,
    autonomy: <AutonomyView canSwitch={admin} />,
  };
  const switcher = (
    <SegmentedControl
      label={QUALITY_TEXT.viewLabel}
      value={view}
      segments={viewsFor(user?.role).map((value) => ({ value, label: QUALITY_TEXT.views[value] }))}
      onChange={(next) => params.update({ view: next === "audits" ? null : next, sample: null, against: null, display: null })}
    />
  );
  return (
    <>
      <PageHeader title={QUALITY_TEXT.title} actions={switcher} />
      {views[view]}
    </>
  );
}

export function QualityScreen() {
  const { user } = useSession();
  return <AreaGuard area="compliance">{user ? <QualityContent /> : null}</AreaGuard>;
}
