import type { UsageFigures } from "@/lib/api/types";
import { UsageStallTable } from "./UsageStallTable";
import { UsageTaskTable } from "./UsageTaskTable";

export function hasUsage(figures: Pick<UsageFigures, "tasks" | "stalls">): boolean {
  return figures.tasks.length > 0 || figures.stalls.length > 0;
}

export function UsageFiguresView({ figures }: { figures: Pick<UsageFigures, "tasks" | "stalls"> }) {
  return (
    <>
      <UsageTaskTable rows={figures.tasks} />
      <UsageStallTable rows={figures.stalls} />
    </>
  );
}
