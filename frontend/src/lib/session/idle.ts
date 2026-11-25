export const ACTIVITY_EVENTS = ["pointerdown", "keydown", "wheel", "touchstart", "scroll"] as const;

type ActivityTarget = Pick<Window, "addEventListener" | "removeEventListener">;

export interface IdleTimerOptions {
  minutes: number;
  onIdle: () => void;
  target?: ActivityTarget;
  now?: () => number;
}

export function startIdleTimer({ minutes, onIdle, target = window, now = Date.now }: IdleTimerOptions): () => void {
  const limit = minutes * 60_000;
  let lastActivity = now();
  let timer: ReturnType<typeof setTimeout> | undefined;
  let stopped = false;

  const stop = (): void => {
    stopped = true;
    clearTimeout(timer);
    for (const name of ACTIVITY_EVENTS) target.removeEventListener(name, onActivity);
  };

  const fire = (): void => {
    if (stopped) return;
    stop();
    onIdle();
  };

  const schedule = (): void => {
    clearTimeout(timer);
    timer = setTimeout(fire, Math.max(0, lastActivity + limit - now()));
  };

  function onActivity(): void {
    if (stopped) return;
    if (now() - lastActivity >= limit) {
      fire();
      return;
    }
    lastActivity = now();
    schedule();
  }

  for (const name of ACTIVITY_EVENTS) target.addEventListener(name, onActivity, { passive: true });
  schedule();
  return stop;
}
