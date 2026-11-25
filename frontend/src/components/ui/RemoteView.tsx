import type { ReactNode } from "react";
import { EmptyState } from "./EmptyState";
import { ErrorState } from "./ErrorState";
import { LoadingState } from "./LoadingState";

export type RemoteStatus<T> =
  | { status: "loading" }
  | { status: "error"; error: string }
  | { status: "success"; data: T };

export interface RemoteText {
  loading: string;
  empty: ReactNode;
  retry: string;
}

interface RemoteViewProps<T> {
  state: RemoteStatus<T>;
  text: RemoteText;
  isEmpty?: (data: T) => boolean;
  emptyAction?: ReactNode;
  onRetry: () => void;
  children: (data: T) => ReactNode;
}

export function RemoteView<T>({ state, text, isEmpty, emptyAction, onRetry, children }: RemoteViewProps<T>) {
  if (state.status === "loading") return <LoadingState label={text.loading} />;
  if (state.status === "error") return <ErrorState message={state.error} retryLabel={text.retry} onRetry={onRetry} />;
  if (isEmpty?.(state.data)) return <EmptyState title={text.empty} action={emptyAction} />;
  return <>{children(state.data)}</>;
}
