import { Spinner } from "./Spinner";

export function LoadingState({ label }: { label: string }) {
  return (
    <div className="flex items-center justify-center px-6 py-12">
      <Spinner label={label} />
    </div>
  );
}
