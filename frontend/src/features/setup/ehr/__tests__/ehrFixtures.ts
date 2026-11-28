import type { EhrConnection, EhrDocumentPage, EhrPullRunPage } from "@/lib/api/types";

export const JWKS_URL = "https://app.example.com/api/ehr/jwks/4f3c2a19b8d7e6f5a4b3c2d1e0f9a8b7";
export const DEFAULT_SCOPES = [
  "system/DocumentReference.read",
  "system/Encounter.read",
  "system/Practitioner.read",
  "system/Binary.read",
];

export const OFF: EhrConnection = {
  available: true,
  status: "off",
  registration: null,
  connection: null,
  default_scopes: DEFAULT_SCOPES,
  last_run: null,
};

export const WITH_KEY: EhrConnection = {
  ...OFF,
  status: "off",
  registration: {
    jwks_url: JWKS_URL,
    key_id: "NzbLsXh8uDCcd-6MNwXF4W_7noWXFZAfHkxZsRGC9Xs",
    algorithm: "RS384",
    key_created_at: "2026-11-27T15:00:00Z",
    grant_type: "client_credentials",
    auth_method: "private_key_jwt",
  },
};

export const PULLING: EhrConnection = {
  ...WITH_KEY,
  status: "pulling",
  connection: {
    base_url: "https://ehr.example.com/fhir/r4",
    token_endpoint: "https://auth.example.com/oauth2/token",
    client_id: "bodha-lakeside",
    scopes: DEFAULT_SCOPES,
    note_types: ["progress", "nursing_facility"],
    start_date: "2026-11-01",
    paused: false,
    saved_at: "2026-11-27T15:05:00Z",
  },
};

export const RUNS: EhrPullRunPage = {
  items: [
    {
      id: "run-2",
      started_at: "2026-11-27T16:00:00Z",
      finished_at: "2026-11-27T16:00:20Z",
      outcome: "failed",
      reason: "token_refused",
      pages: 0,
      accepted: 0,
      duplicates: 0,
      refused: 0,
      skipped: 0,
    },
    {
      id: "run-1",
      started_at: "2026-11-27T15:45:00Z",
      finished_at: "2026-11-27T15:46:00Z",
      outcome: "succeeded",
      reason: null,
      pages: 1,
      accepted: 3,
      duplicates: 1,
      refused: 1,
      skipped: 0,
    },
  ],
  total: 2,
  offset: 0,
  page_size: 20,
};

export const DOCUMENTS: EhrDocumentPage = {
  items: [
    { id: "doc-2", fetched_at: "2026-11-27T15:45:30Z", document_id: "d-772", outcome: "refused", reason: "no_provider", note_id: null },
    { id: "doc-1", fetched_at: "2026-11-27T15:45:10Z", document_id: "d-771", outcome: "accepted", reason: null, note_id: "note-1" },
  ],
  total: 2,
  offset: 0,
  page_size: 50,
};

export const NO_RUNS: EhrPullRunPage = { items: [], total: 0, offset: 0, page_size: 20 };
export const NO_DOCUMENTS: EhrDocumentPage = { items: [], total: 0, offset: 0, page_size: 50 };
