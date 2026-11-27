"use client";

import "./globals.css";
import { ErrorScreen } from "@/components/shared/errors/ErrorScreen";
import { SHARED_TEXT } from "@/components/shared/strings";
import { Button } from "@/components/ui/Button";

export default function GlobalError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
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
