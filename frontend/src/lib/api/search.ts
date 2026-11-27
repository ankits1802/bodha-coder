import { request } from "./client";
import type { SearchResults } from "./types";

export function searchNotes(text: string): Promise<SearchResults> {
  return request<SearchResults>("/api/search", { query: { q: text } });
}
