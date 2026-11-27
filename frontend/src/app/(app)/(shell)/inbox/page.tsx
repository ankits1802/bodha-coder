import type { Metadata } from "next";
import { Suspense } from "react";
import { InboxScreen } from "@/features/inbox/InboxScreen";
import { INBOX_TEXT } from "@/features/inbox/strings";

export const metadata: Metadata = { title: INBOX_TEXT.title };

export default function InboxPage() {
  return (
    <Suspense>
      <InboxScreen />
    </Suspense>
  );
}
