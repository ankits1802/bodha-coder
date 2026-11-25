import { Button } from "./Button";

interface ErrorStateProps {
  message: string;
  retryLabel?: string;
  onRetry?: () => void;
}

export function ErrorState({ message, retryLabel, onRetry }: ErrorStateProps) {
  return (
    <div role="alert" className="flex flex-col items-center justify-center gap-3 px-6 py-12 text-center">
      <p className="m-0 flex items-center gap-2 text-body-lg text-label">
        <span aria-hidden="true" className="size-2 flex-none rounded-full bg-bad" />
        {message}
      </p>
      {onRetry && retryLabel ? (
        <Button size="sm" onClick={onRetry}>
          {retryLabel}
        </Button>
      ) : null}
    </div>
  );
}
