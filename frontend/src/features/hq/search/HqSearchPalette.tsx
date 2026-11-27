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
import { formatCount } from "@/lib/format";
import { canSearchPlatform } from "@/lib/roles";
import { useSession } from "@/lib/session/useSession";
import { HQ_TEXT } from "../strings";
import { searchOptions, type SearchOption } from "./hqSearchModel";
import { HqSearchList } from "./HqSearchList";
import { useHqSearch } from "./useHqSearch";

const words = HQ_TEXT.search;
const REMOTE_TEXT = { loading: words.searching, empty: words.empty, retry: HQ_TEXT.retry };
const MAX_LENGTH = 100;

function SearchBox({ onOpen }: { onOpen: (option: SearchOption) => void }) {
  const [text, setText] = useState("");
  const listId = useId();
  const search = useHqSearch(text);
  const state = search.remote.state;
  const options = search.ready && state.status === "success" ? searchOptions(state.data) : [];
  const { current, setActive, onKeyDown } = useActiveOption(options, onOpen);
  const listed = options.length > 0;

  return (
    <div className="flex flex-col gap-3">
      <Input
        type="search"
        role="combobox"
        aria-label={words.label}
        aria-expanded={listed}
        aria-controls={listed ? listId : undefined}
        aria-autocomplete="list"
        aria-activedescendant={listed ? optionId(listId, current) : undefined}
        placeholder={words.placeholder}
        autoFocus
        maxLength={MAX_LENGTH}
        value={text}
        onChange={(event) => {
          setText(event.target.value);
          setActive(0);
        }}
        onKeyDown={onKeyDown}
      />
      {search.ready ? (
        <RemoteView
          state={state}
          text={REMOTE_TEXT}
          isEmpty={(data) => data.practices.length + data.people.length === 0}
          onRetry={search.remote.reload}
        >
          {(data) => (
            <>
              <HqSearchList listId={listId} options={options} active={current} onActive={setActive} onOpen={onOpen} />
              {data.practices.length >= data.limit || data.people.length >= data.limit ? (
                <p className="m-0 text-caption text-secondary">{words.firstResults(formatCount(data.limit))}</p>
              ) : null}
            </>
          )}
        </RemoteView>
      ) : null}
    </div>
  );
}

export function HqSearchPalette() {
  const { user } = useSession();
  const router = useRouter();
  const allowed = canSearchPlatform(user);
  const open = useOpenOverlay() === "search";
  useShortcuts("global", { search: allowed ? () => openOverlay("search") : undefined });
  if (!allowed) return null;

  function choose(option: SearchOption): void {
    if (!option.href) return;
    closeOverlay();
    router.push(option.href);
  }

  return (
    <Dialog open={open} onClose={closeOverlay} title={words.title} size="lg" footer={<Button onClick={closeOverlay}>{words.close}</Button>}>
      {open ? <SearchBox onOpen={choose} /> : null}
    </Dialog>
  );
}
