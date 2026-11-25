import { Button } from "@/components/ui/Button";
import { UPLOAD_TEXT } from "../strings";

interface UploadBarProps {
  count: number;
  canStart: boolean;
  pending: boolean;
  error: string | null;
  onStart: () => void;
}

export function UploadBar({ count, canStart, pending, error, onStart }: UploadBarProps) {
  const words = UPLOAD_TEXT.bar;
  return (
    <div className="sticky bottom-5 flex flex-wrap items-center justify-between gap-4 rounded-float bg-surface/95 py-3 pr-3 pl-5 shadow-float">
      <span className="flex flex-col">
        <span className="font-semibold">{words.ready(count)}</span>
        {error ? (
          <span role="alert" className="text-footnote text-bad-text">
            {error}
          </span>
        ) : null}
      </span>
      <Button variant="primary" onClick={onStart} disabled={!canStart} pending={pending}>
        {words.start(count)}
      </Button>
    </div>
  );
}
