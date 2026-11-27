"use client";

import { showToast } from "@/components/shared/toast/toastStore";
import { PageHeader } from "@/components/ui/PageHeader";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { RemoteView } from "@/components/ui/RemoteView";
import { useQueryParams } from "@/hooks/useQueryParams";
import { useRemote } from "@/hooks/useRemote";
import { getSetup } from "@/lib/api/practice";
import type { PracticeSetup } from "@/lib/api/types";
import { ChecksPanel } from "./ChecksPanel";
import { ReviewSettingsPanel } from "./ReviewSettingsPanel";
import { SectionContent } from "./SectionContent";
import { SetupNav } from "./SetupNav";
import { isNavKey, nextIncomplete } from "./setupModel";
import { SETUP_TEXT, type SetupNavKey } from "./strings";
import { IntakeSettings } from "@/components/shared/intake/IntakeSettings";

export function SetupScreen() {
  const remote = useRemote("practice-setup", getSetup);
  const query = useQueryParams();
  const requested = query.get("section");
  const selected: SetupNavKey = isNavKey(requested) ? requested : "practice_details";
  const setup = remote.state.status === "success" ? remote.state.data : null;

  function sectionSaved(data: PracticeSetup): void {
    showToast(SETUP_TEXT.sectionSaved(SETUP_TEXT.sections[selected]));
    remote.reload();
    const next = nextIncomplete(data, selected);
    if (next) query.update({ section: next });
  }

  return (
    <>
      <PageHeader
        title={SETUP_TEXT.title}
        subtitle={setup ? SETUP_TEXT.progress(setup.complete, setup.total) : undefined}
        actions={
          setup ? (
            <span className="block w-60">
              <ProgressBar label={SETUP_TEXT.progressLabel} value={setup.complete} max={setup.total} tone="ok" />
            </span>
          ) : null
        }
      />
      <RemoteView
        state={remote.state}
        text={{ loading: SETUP_TEXT.loading, empty: SETUP_TEXT.empty, retry: SETUP_TEXT.retry }}
        isEmpty={(data) => Object.keys(data.sections).length === 0}
        onRetry={remote.reload}
      >
        {(data) => (
          <div className="flex flex-wrap items-start gap-6">
            <SetupNav setup={data} selected={selected} />
            <div className="flex min-w-0 flex-[999_1_32rem] flex-col gap-5">
              <SectionContent
                key={selected}
                navKey={selected}
                setup={data}
                onSaved={remote.reload}
                onSectionSaved={() => sectionSaved(data)}
              />
              <ChecksPanel checks={data.checks} onSaved={remote.reload} />
              <ReviewSettingsPanel settings={data.review} onSaved={remote.reload} />
              <IntakeSettings />
            </div>
          </div>
        )}
      </RemoteView>
    </>
  );
}
