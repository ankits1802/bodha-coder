import type { Metadata } from "next";
import { ErrorScreen } from "@/components/shared/errors/ErrorScreen";
import { SHARED_TEXT } from "@/components/shared/strings";
import { ButtonLink } from "@/components/ui/ButtonLink";

export const metadata: Metadata = { title: SHARED_TEXT.errors.notFound };

export default function NotFound() {
  const words = SHARED_TEXT.errors;
  return (
    <ErrorScreen
      code={words.notFoundCode}
      title={words.notFound}
      actions={
        <ButtonLink href="/" variant="primary">
          {words.home}
        </ButtonLink>
      }
    />
  );
}
