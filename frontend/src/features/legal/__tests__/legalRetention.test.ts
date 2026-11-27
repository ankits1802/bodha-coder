import { describe, expect, it } from "vitest";
import { LEGAL_SLUGS, type LegalSlug } from "@/components/shared/legal/legalLinks";
import { SERVICE_FACTS } from "../config";
import { LEGAL_DOCUMENTS } from "../documents";
import { documentTexts } from "../placeholders";

function textOf(slug: LegalSlug): string {
  return documentTexts(LEGAL_DOCUMENTS[slug]).join(" ");
}

describe("retention statements", () => {
  it("keeps records, backups, stored file versions and logs for seven years", () => {
    expect(SERVICE_FACTS.recordRetentionDays).toBe(2557);
    expect([
      SERVICE_FACTS.recordRetentionYears,
      SERVICE_FACTS.accessLogYears,
      SERVICE_FACTS.backupYears,
      SERVICE_FACTS.documentLockYears,
      SERVICE_FACTS.logYears,
    ]).toEqual([7, 7, 7, 7, 7]);
    expect(SERVICE_FACTS.accessLogMaxYears).toBe(10);
  });

  it("promises no deletion sooner than the retention period on any page", () => {
    const everything = LEGAL_SLUGS.map(textOf).join(" ");
    expect(everything).not.toMatch(/\b(35|400) days\b/);
    expect(everything).not.toMatch(/6 years by default/);
    expect(everything).not.toMatch(/delete[^.]*within \d+ days/i);
    expect(everything).not.toMatch(/sooner if you ask in writing/);
  });

  it("states the closing, the seven years after it and the purge in the Terms", () => {
    const terms = textOf("terms");
    expect(terms).toContain("for at least 7 years (2557 days) from the date each was created");
    expect(terms).toContain("for at least 7 years after the account is closed.");
    expect(terms).toContain("A note uploaded by mistake can be voided");
  });

  it("makes destruction infeasible during the retention period in the BAA and keeps its protections", () => {
    const baa = textOf("baa");
    expect(baa).toContain("returning or destroying the PHI kept for the retention period is infeasible until that period ends");
    expect(baa).toContain("Business Associate will extend the protections of this BAA to that PHI");
    expect(baa).toContain("After the retention period ends, Business Associate will purge");
  });

  it("names the storage lock, the backups and the log retention on the Security Overview", () => {
    const security = textOf("security");
    expect(security).toContain("Amazon S3 Object Lock in governance mode");
    expect(security).toContain("monthly backups are kept for 7 years in AWS Backup");
    expect(security).toContain("Application logs are kept in Amazon CloudWatch for 7 years");
    expect(security).toContain("AWS CloudTrail");
  });
});
