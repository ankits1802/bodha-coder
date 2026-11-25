"use client";

import { useRemote } from "@/hooks/useRemote";
import { getPlaces } from "@/lib/api/uploads";

export function usePlaceNames(enabled: boolean): Record<string, string> {
  const places = useRemote(enabled ? "today-places" : null, getPlaces);
  if (places.state.status !== "success") return {};
  return Object.fromEntries(places.state.data.map((place) => [place.code, place.name]));
}
