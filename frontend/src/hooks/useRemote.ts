"use client";

import { useCallback, useEffect, useEffectEvent, useState } from "react";
import type { RemoteStatus } from "@/components/ui/RemoteView";
import { messageOf } from "@/lib/api/errors";

type Settled<T> = Exclude<RemoteStatus<T>, { status: "loading" }>;

interface Snapshot<T> {
  key: string;
  round: number;
  state: Settled<T>;
}

export interface Remote<T> {
  state: RemoteStatus<T>;
  refreshing: boolean;
  reload: () => void;
  replace: (data: T) => void;
}

const LOADING = { status: "loading" } as const;

export function useRemote<T>(key: string | null, load: () => Promise<T>): Remote<T> {
  const [round, setRound] = useState(0);
  const [snapshot, setSnapshot] = useState<Snapshot<T> | null>(null);
  const fetchData = useEffectEvent(load);

  useEffect(() => {
    if (key === null) return;
    let live = true;
    fetchData().then(
      (data) => {
        if (live) setSnapshot({ key, round, state: { status: "success", data } });
      },
      (error: unknown) => {
        if (live) setSnapshot({ key, round, state: { status: "error", error: messageOf(error) } });
      },
    );
    return () => {
      live = false;
    };
  }, [key, round]);

  const reload = useCallback(() => setRound((value) => value + 1), []);
  const replace = useCallback(
    (data: T) => {
      if (key !== null) setSnapshot({ key, round, state: { status: "success", data } });
    },
    [key, round],
  );

  const current = snapshot !== null && snapshot.key === key;
  const state: RemoteStatus<T> = current ? snapshot.state : LOADING;
  return { state, refreshing: current && snapshot.round !== round, reload, replace };
}
