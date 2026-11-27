"use client";

import { useCallback, useEffect, useEffectEvent, useRef, useState } from "react";
import type { RemoteStatus } from "@/components/ui/RemoteView";
import { messageOf } from "@/lib/api/errors";
import { loadRemote, readRemote, writeRemote } from "./remoteCache";

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

export function useRemote<T>(key: string | null, load: () => Promise<T>, keepSeconds = 0): Remote<T> {
  const [round, setRound] = useState(0);
  const [snapshot, setSnapshot] = useState<Snapshot<T> | null>(null);
  const forced = useRef(false);
  const fetchData = useEffectEvent((target: string, join: boolean) => loadRemote(target, load, keepSeconds, join));

  useEffect(() => {
    if (key === null) return;
    const fresh = forced.current;
    forced.current = false;
    const hit = fresh ? undefined : readRemote<T>(key);
    if (hit !== undefined) {
      setSnapshot({ key, round, state: { status: "success", data: hit } });
      return;
    }
    let live = true;
    fetchData(key, !fresh).then(
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

  const reload = useCallback(() => {
    forced.current = true;
    setRound((value) => value + 1);
  }, []);
  const replace = useCallback(
    (data: T) => {
      if (key === null) return;
      writeRemote(key, data);
      setSnapshot({ key, round, state: { status: "success", data } });
    },
    [key, round],
  );

  const current = snapshot !== null && snapshot.key === key;
  const cached = !current && key !== null ? readRemote<T>(key) : undefined;
  const state: RemoteStatus<T> = current ? snapshot.state : cached !== undefined ? { status: "success", data: cached } : LOADING;
  return { state, refreshing: current && snapshot.round !== round, reload, replace };
}
