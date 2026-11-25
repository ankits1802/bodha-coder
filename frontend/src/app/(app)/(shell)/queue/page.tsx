import type { Metadata } from "next";
import { Suspense } from "react";
import { QueueScreen } from "@/features/queue/QueueScreen";
import { QUEUE_TEXT } from "@/features/queue/strings";

export const metadata: Metadata = { title: QUEUE_TEXT.title };

export default function QueuePage() {
  return (
    <Suspense>
      <QueueScreen />
    </Suspense>
  );
}
