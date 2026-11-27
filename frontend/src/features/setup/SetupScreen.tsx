"use client";

import { showToast } from "@/components/shared/toast/toastStore";
import { PageHeader } from "@/components/ui/PageHeader";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { RemoteView } from "@/components/ui/RemoteView";
import { useAction } from "@/hooks/useAction";
import { useQueryParams } from "@/hooks/useQueryParams";
import { usePracticeSetup } from "@/hooks/usePracticeSetup";
import { getSetup } from "@/lib/api/practice";
import { isSetupOpen } from "@/lib/paths";
import { SectionContent } from "./SectionContent";
import { SetupNav } from "./SetupNav";
import { isNavKey, nextIncomplete } from "./setupModel";
import { SETUP_TEXT, type SetupNavKey } from "./strings";

export function SetupScreen() {
  const remote = usePracticeSetup();
  const refresh = useAction(getSetup);
  const query = useQueryParams();
  const requested = query.get("section");
  const selected: SetupNavKey = isNavKey(requested) ? requested : "practice_details";
  const open = query.get("open");
  const setup = remote.state.status === "success" ? remote.state.data : null;

  async function sectionSaved(): Promise<void> {
    showToast(SETUP_TEXT.sectionSaved(SETUP_TEXT.sections[selected]));
    const outcome = await refresh.run();
    if (!outcome.ok) {
      showToast(outcome.error);
      return;
    }
    remote.replace(outcome.value);
    const next = nextIncomplete(outcome.value, selected);
    if (next) query.update({ section: next });
  }

  return (
    <>
      <PageHeader
        title={SETUP_TEXT.title}
        subtitle={setup ? SETUP_TEXT.progress(setup.complete, setup.total) : undefined}
        actions={
          setup ? (
            <span className="block w-60 max-w-full">
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
                open={isSetupOpen(open) ? open : null}
                onOpened={() => query.update({ open: null })}
                onSaved={remote.reload}
                onSectionSaved={() => void sectionSaved()}
              />
            </div>
          </div>
        )}
      </RemoteView>
    </>
  );
}
