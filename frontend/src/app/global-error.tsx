"use client";

import { useEffect } from "react";
import "./globals.css";
import { ErrorScreen } from "@/components/shared/errors/ErrorScreen";
import { SHARED_TEXT } from "@/components/shared/strings";
import { Button } from "@/components/ui/Button";
import { reportError } from "@/lib/errorReports/client";

export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => reportError(error), [error]);
  return (
    <html lang="en">
      <body>
        <ErrorScreen
          title={SHARED_TEXT.errors.failed}
          actions={
            <Button variant="primary" onClick={reset}>
              {SHARED_TEXT.errors.retry}
            </Button>
          }
        />
      </body>
    </html>
  );
}
