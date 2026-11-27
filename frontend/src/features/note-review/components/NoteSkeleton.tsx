import { Panel } from "@/components/ui/Panel";
import { SkeletonBlock, SkeletonFrame } from "@/components/ui/Skeleton";

const LINES = ["w-11/12", "w-10/12", "w-full", "w-9/12", "w-11/12", "w-8/12", "w-10/12", "w-7/12"];

export function NoteSkeleton({ label }: { label: string }) {
  return (
    <SkeletonFrame label={label}>
      <div className="mx-auto flex w-full max-w-review flex-col gap-6 px-4 pt-8 pb-10 sm:px-8">
        <div className="flex flex-col gap-3">
          <SkeletonBlock className="h-9 w-72" />
          <SkeletonBlock className="h-4 w-96 max-w-full" />
        </div>
        <Panel as="div" className="flex flex-col gap-3 px-5.5 py-5">
          <SkeletonBlock className="h-4 w-28" />
          <SkeletonBlock className="h-7 w-64" />
        </Panel>
        <div className="flex flex-wrap items-start gap-6">
          <Panel as="div" className="flex min-w-0 flex-[1_1_31rem] flex-col gap-3 px-6.5 py-6">
            {LINES.map((width, index) => (
              <SkeletonBlock key={index} className={`h-4 ${width}`} />
            ))}
          </Panel>
          <Panel as="div" className="flex min-w-0 flex-[1_1_34rem] flex-col gap-4 px-5 py-5">
            <SkeletonBlock className="h-7 w-80 max-w-full" />
            <SkeletonBlock className="h-16 w-full" />
            <SkeletonBlock className="h-16 w-full" />
          </Panel>
        </div>
      </div>
    </SkeletonFrame>
  );
}
