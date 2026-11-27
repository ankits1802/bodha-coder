"use client";

import { AuthFrame } from "@/components/shared/AuthFrame";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { useFragmentToken } from "@/hooks/useFragmentToken";
import { useRemote } from "@/hooks/useRemote";
import { SIGN_UP_PATH } from "@/lib/api/auth";
import { getJoinPage } from "@/lib/api/signupJoin";
import { JoinChoices } from "./JoinChoices";
import { SIGN_UP_TEXT } from "./strings";

function Expired() {
  return (
    <div className="flex flex-col">
      <ErrorState message={SIGN_UP_TEXT.join.expired} />
      <ButtonLink href={SIGN_UP_PATH} variant="plain" size="sm" className="self-center">
        {SIGN_UP_TEXT.startAgain}
      </ButtonLink>
    </div>
  );
}

function Offer({ token }: { token: string }) {
  const page = useRemote(`join-page:${token}`, () => getJoinPage(token));
  if (page.state.status === "loading") return <LoadingState label={SIGN_UP_TEXT.loading} />;
  if (page.state.status === "error") return <Expired />;
  return <JoinChoices token={token} page={page.state.data} />;
}

export function JoinScreen() {
  const token = useFragmentToken();
  return (
    <AuthFrame>
      {token === undefined ? <LoadingState label={SIGN_UP_TEXT.loading} /> : null}
      {token === null ? <Expired /> : null}
      {token ? <Offer token={token} /> : null}
    </AuthFrame>
  );
}
