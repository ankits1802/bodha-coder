"use client";

import { LOOKUP_SECONDS } from "@/hooks/remoteCache";
import { useRemote } from "@/hooks/useRemote";
import { getPlaces } from "@/lib/api/uploads";

export type PlaceNames = Record<string, string>;

export function usePlaceNames(): PlaceNames {
  const places = useRemote("places", getPlaces, LOOKUP_SECONDS);
  if (places.state.status !== "success") return {};
  return Object.fromEntries(places.state.data.map((place) => [place.code, place.name]));
}

export function placeName(names: PlaceNames, code: string | null): string | null {
  if (code === null) return null;
  return names[code] ?? code;
}
