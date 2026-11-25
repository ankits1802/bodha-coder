import type { ReactNode } from "react";

export function TabSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="flex flex-col gap-2 border-t border-hairline px-5 py-4 first:border-t-0">
      <h3 className="m-0 font-sans text-subhead font-semibold text-secondary">{title}</h3>
      {children}
    </section>
  );
}
