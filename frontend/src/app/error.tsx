"use client";

import { useEffect } from "react";
import { ErrorScreen } from "@/components/shared/errors/ErrorScreen";
import { SHARED_TEXT } from "@/components/shared/strings";
import { Button } from "@/components/ui/Button";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { reportError } from "@/lib/errorReports/client";

export default function RouteError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => reportError(error), [error]);
  const words = SHARED_TEXT.errors;
  return (
    <ErrorScreen
      title={words.failed}
      actions={
        <>
          <Button variant="primary" onClick={reset}>
            {words.retry}
          </Button>
          <ButtonLink href="/" variant="plain">
            {words.home}
          </ButtonLink>
        </>
      }
    />
  );
}
