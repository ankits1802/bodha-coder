"use client";

import { useState, type ReactNode } from "react";
import { Button } from "@/components/ui/Button";
import { useSession } from "@/lib/session/useSession";
import { SHARED_TEXT } from "../strings";
import { Sidebar } from "./Sidebar";

const SIDEBAR_ID = "app-sidebar";

export function AppShell({ children }: { children: ReactNode }) {
  const { user } = useSession();
  const [menuOpen, setMenuOpen] = useState(false);
  if (!user) return null;

  return (
    <div className="flex min-h-screen flex-col lg:flex-row">
      <a
        href="#main"
        className="sr-only rounded-control bg-surface px-3 py-2 focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50"
      >
        {SHARED_TEXT.skipToContent}
      </a>
      <div className="flex items-center justify-between border-b border-separator bg-sidebar px-4 py-2.5 lg:hidden">
        <span className="text-body-lg font-semibold">{SHARED_TEXT.brand}</span>
        <Button
          variant="plain"
          size="sm"
          aria-expanded={menuOpen}
          aria-controls={SIDEBAR_ID}
          onClick={() => setMenuOpen((open) => !open)}
        >
          {menuOpen ? SHARED_TEXT.closeMenu : SHARED_TEXT.menu}
        </Button>
      </div>
      <div
        id={SIDEBAR_ID}
        className={`${menuOpen ? "block" : "hidden"} lg:sticky lg:top-0 lg:block lg:h-screen lg:w-58 lg:flex-none lg:overflow-y-auto`}
      >
        <Sidebar user={user} onNavigate={() => setMenuOpen(false)} />
      </div>
      <main id="main" tabIndex={-1} className="min-w-0 flex-1 px-4 pt-8 pb-12 outline-none sm:px-8 lg:px-12 lg:pt-10">
        <div className="flex max-w-content flex-col gap-6">{children}</div>
      </main>
    </div>
  );
}
