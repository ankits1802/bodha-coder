import type { ReactNode } from "react";
import { SHARED_TEXT } from "./strings";

export function AuthFrame({ children }: { children: ReactNode }) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-surface px-4 py-12">
      <div className="flex w-full max-w-90 flex-col gap-10">
        <div className="flex flex-col gap-2 text-center">
          <h1 className="m-0 text-hero-sm font-bold tracking-title">{SHARED_TEXT.brand}</h1>
          <p className="m-0 text-headline text-secondary tracking-snug">{SHARED_TEXT.tagline}</p>
        </div>
        {children}
      </div>
    </main>
  );
}
