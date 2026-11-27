"use client";

import { ErrorScreen } from "@/components/shared/errors/ErrorScreen";
import { SHARED_TEXT } from "@/components/shared/strings";
import { Button } from "@/components/ui/Button";
import { ButtonLink } from "@/components/ui/ButtonLink";

export default function RouteError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
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
