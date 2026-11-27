"use client";

import { Drawer } from "@/components/ui/Drawer";
import type { NoteDetail } from "@/lib/api/types";
import { REVIEW_TEXT } from "../strings";
import { HistoryContent } from "./HistoryContent";

interface HistoryDrawerProps {
  open: boolean;
  detail: NoteDetail;
  onClose: () => void;
}

export function HistoryDrawer({ open, detail, onClose }: HistoryDrawerProps) {
  return (
    <Drawer open={open} onClose={onClose} title={REVIEW_TEXT.historyOpen} closeLabel={REVIEW_TEXT.historyClose}>
      <HistoryContent detail={detail} />
    </Drawer>
  );
}
