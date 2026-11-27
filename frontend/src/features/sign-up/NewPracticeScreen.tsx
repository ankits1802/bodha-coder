"use client";

import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { PageHeader } from "@/components/ui/PageHeader";
import { Panel } from "@/components/ui/Panel";
import { useSignInOptions } from "@/hooks/useSignInOptions";
import { NewPracticeForm } from "./NewPracticeForm";
import { SIGN_UP_TEXT } from "./strings";

export function NewPracticeScreen() {
  const options = useSignInOptions();
  const { state } = options;
  const open = state.status === "success" && state.data.signup.enabled;
  return (
    <>
      <PageHeader title={SIGN_UP_TEXT.newPracticeTitle} />
      <Panel className="max-w-120 p-5">
        {state.status === "loading" ? <LoadingState label={SIGN_UP_TEXT.loading} /> : null}
        {state.status === "error" ? (
          <ErrorState message={state.error} retryLabel={SIGN_UP_TEXT.retry} onRetry={options.reload} />
        ) : null}
        {state.status === "success" && !open ? <ErrorState message={SIGN_UP_TEXT.unavailable} /> : null}
        {state.status === "success" && open ? <NewPracticeForm options={state.data.signup} /> : null}
      </Panel>
    </>
  );
}
