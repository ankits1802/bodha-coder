"use client";

import { useRouter } from "next/navigation";
import { useId, useState } from "react";
import { closeOverlay, openOverlay, useOpenOverlay } from "@/components/shared/overlays";
import { useShortcuts } from "@/components/shared/shortcuts/useShortcuts";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { Input } from "@/components/ui/Input";
import { RemoteView } from "@/components/ui/RemoteView";
import { optionId, useActiveOption } from "@/hooks/useActiveOption";
import type { NoteSummary } from "@/lib/api/types";
import { formatCount } from "@/lib/format";
import { canSearch } from "@/lib/roles";
import { useSession } from "@/lib/session/useSession";
import { SearchResultList } from "./SearchResultList";
import { SEARCH_TEXT } from "./strings";
import { useNoteSearch } from "./useNoteSearch";

const REMOTE_TEXT = { loading: SEARCH_TEXT.searching, empty: SEARCH_TEXT.empty, retry: SEARCH_TEXT.retry };

function SearchBox({ onOpen }: { onOpen: (note: NoteSummary) => void }) {
  const [text, setText] = useState("");
  const listId = useId();
  const search = useNoteSearch(text);
  const state = search.remote.state;
  const items = search.ready && state.status === "success" ? state.data.items : [];
  const { current, setActive, onKeyDown } = useActiveOption(items, onOpen);
  const listed = items.length > 0;

  return (
    <div className="flex flex-col gap-3">
      <Input
        type="search"
        role="combobox"
        aria-label={SEARCH_TEXT.label}
        aria-expanded={listed}
        aria-controls={listed ? listId : undefined}
        aria-autocomplete="list"
        aria-activedescendant={listed ? optionId(listId, current) : undefined}
        placeholder={SEARCH_TEXT.placeholder}
        autoFocus
        maxLength={100}
        value={text}
        onChange={(event) => {
          setText(event.target.value);
          setActive(0);
        }}
        onKeyDown={onKeyDown}
      />
      {search.ready ? (
        <RemoteView state={state} text={REMOTE_TEXT} isEmpty={(data) => data.items.length === 0} onRetry={search.remote.reload}>
          {(data) => (
            <>
              <SearchResultList listId={listId} items={data.items} active={current} onActive={setActive} onOpen={onOpen} />
              {data.items.length >= data.limit ? (
                <p className="m-0 text-caption text-secondary">{SEARCH_TEXT.firstResults(formatCount(data.limit))}</p>
              ) : null}
            </>
          )}
        </RemoteView>
      ) : null}
    </div>
  );
}

export function SearchPalette() {
  const { user } = useSession();
  const router = useRouter();
  const allowed = canSearch(user);
  const open = useOpenOverlay() === "search";
  useShortcuts("global", { search: allowed ? () => openOverlay("search") : undefined });
  const openNote = (note: NoteSummary) => {
    closeOverlay();
    router.push(`/notes/${encodeURIComponent(note.id)}`);
  };
  if (!allowed) return null;

  return (
    <Dialog
      open={open}
      onClose={closeOverlay}
      title={SEARCH_TEXT.title}
      size="lg"
      footer={<Button onClick={closeOverlay}>{SEARCH_TEXT.close}</Button>}
    >
      <SearchBox onOpen={openNote} />
    </Dialog>
  );
}
