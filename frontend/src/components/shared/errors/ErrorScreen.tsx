import type { ReactNode } from "react";
import { SHARED_TEXT } from "../strings";

export function ErrorScreen({ code, title, actions }: { code?: string; title: string; actions: ReactNode }) {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 bg-page px-6 text-center">
      <span className="text-body-lg font-semibold tracking-snug text-label">{SHARED_TEXT.brand}</span>
      {code ? <span className="font-display text-display-lg font-bold tracking-tightest text-label tabular-nums">{code}</span> : null}
      <h1 className="m-0 font-display text-title2 font-semibold tracking-title text-label">{title}</h1>
      <div className="flex flex-wrap items-center justify-center gap-3">{actions}</div>
    </main>
  );
}
