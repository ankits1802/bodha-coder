import type { EmailIntake, IntakeMessagePage } from "@/lib/api/types";

export const ADDRESS = "k3j8w2q9x7m4n5p6@intake.bodhaai.co";
export const NEXT_ADDRESS = "a2b3c4d5e6f7g2h3@intake.bodhaai.co";

export const OFF: EmailIntake = { available: true, address: null, address_since: null, previous: [], senders: [] };

export const RECEIVING: EmailIntake = {
  ...OFF,
  address: ADDRESS,
  address_since: "2026-11-28T09:00:00Z",
  senders: [{ id: "s1", pattern: "lakeside.example.com", kind: "domain", added_at: "2026-11-28T09:01:00Z" }],
};

export const EMPTY_PAGE: IntakeMessagePage = { items: [], total: 0, offset: 0, page_size: 50 };

export const PAGE: IntakeMessagePage = {
  ...EMPTY_PAGE,
  total: 2,
  items: [
    {
      id: "m1",
      received_at: "2026-11-28T10:00:00Z",
      sender: "scans@lakeside.example.com",
      outcome: "accepted",
      reason: null,
      accepted_files: 1,
      refused_files: 1,
      files: [
        { outcome: "accepted", reason: null, note_id: "n1" },
        { outcome: "refused", reason: "only PDF files are read", note_id: null },
      ],
    },
    {
      id: "m2",
      received_at: "2026-11-28T10:05:00Z",
      sender: "someone@elsewhere.example.org",
      outcome: "refused",
      reason: "sender_not_allowed",
      accepted_files: 0,
      refused_files: 0,
      files: [],
    },
  ],
};
