import type { Box } from "./tourPlacement";

const RING =
  "pointer-events-none fixed top-0 left-0 rounded-field shadow-[0_0_0_200vmax_var(--color-scrim)] outline-2 outline-white motion-safe:transition-transform motion-safe:duration-200 motion-safe:ease-out";

export function TourSpotlight({ box }: { box: Box | null }) {
  if (box === null) return <div aria-hidden="true" data-spotlight="none" className="fixed inset-0 bg-scrim" />;
  return (
    <div
      aria-hidden="true"
      data-spotlight="target"
      className={RING}
      style={{ width: box.width, height: box.height, transform: `translate(${box.left}px, ${box.top}px)` }}
    />
  );
}
