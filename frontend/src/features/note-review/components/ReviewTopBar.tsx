"use client";

import Link from "next/link";
import { shortcutTitle } from "@/components/shared/shortcuts/registry";
import { useIsMac } from "@/components/shared/shortcuts/useIsMac";
import { Button } from "@/components/ui/Button";
import { buttonClasses } from "@/components/ui/buttonStyles";
import { Chevron } from "@/components/ui/Chevron";
import { REVIEW_TEXT } from "../strings";
import type { Neighbours } from "../useNoteData";
import { ReplacePdfButton } from "./ReplacePdfButton";

export interface ReplacePdf {
  noteId: string;
  onReplaced: () => void;
}

interface ReviewTopBarProps {
  backHref: string;
  title: string | null;
  neighbours: Neighbours;
  onGo: (noteId: string) => void;
  onOpenPdf: (() => void) | null;
  pdfPending: boolean;
  replacePdf?: ReplacePdf | null;
}

function StepButton({ target, label, direction, onGo }: { target: string | null; label: string; direction: "left" | "right"; onGo: (id: string) => void }) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      disabled={target === null}
      onClick={() => target && onGo(target)}
      className="flex h-7 w-8 cursor-pointer items-center justify-center rounded-nav text-label hover:bg-surface disabled:cursor-not-allowed disabled:text-quaternary disabled:hover:bg-transparent"
    >
      <Chevron direction={direction} className="flex-none" />
    </button>
  );
}

export function ReviewTopBar({ backHref, title, neighbours, onGo, onOpenPdf, pdfPending, replacePdf = null }: ReviewTopBarProps) {
  const mac = useIsMac();
  return (
    <div className="sticky top-0 z-10 flex min-h-14 flex-wrap items-center justify-between gap-3 border-b border-separator bg-surface/95 px-4 py-2">
      <Link href={backHref} className={buttonClasses("plain", "md", "px-3")}>
        <Chevron direction="left" className="flex-none" />
        {REVIEW_TEXT.backToQueue}
      </Link>
      <div className="flex min-w-0 flex-col items-center leading-tight">
        {title ? <span className="truncate text-callout font-semibold">{title}</span> : null}
        {neighbours.index !== null ? (
          <span className="text-caption text-secondary">{REVIEW_TEXT.position(neighbours.index, neighbours.total)}</span>
        ) : null}
      </div>
      <div className="flex items-center gap-2">
        <div className="flex rounded-segment bg-control p-0.5">
          <StepButton target={neighbours.previous} label={shortcutTitle("previousNote", mac)} direction="left" onGo={onGo} />
          <StepButton target={neighbours.next} label={shortcutTitle("nextNote", mac)} direction="right" onGo={onGo} />
        </div>
        {onOpenPdf ? (
          <Button onClick={onOpenPdf} pending={pdfPending}>
            {REVIEW_TEXT.originalPdf}
          </Button>
        ) : null}
        {replacePdf ? <ReplacePdfButton noteId={replacePdf.noteId} onReplaced={replacePdf.onReplaced} /> : null}
      </div>
    </div>
  );
}
