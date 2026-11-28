import { describe, expect, it } from "vitest";
import type { SsoCertificate, SsoVersion } from "@/lib/api/types";
import { draftFrom, requestFrom, toggled, withImported, withoutCertificate } from "../ssoDraft";

function certificate(value: string): SsoCertificate {
  return { value, subject: `CN=${value}`, expires_at: "2027-11-28T00:00:00+00:00", sha256: `${value}-sha` };
}

const SAVED: SsoVersion = {
  version: 3,
  identity_provider: {
    entity_id: "https://idp.lakeside.example.com/saml",
    sso_url: "https://idp.lakeside.example.com/sso",
    metadata_url: null,
    certificates: [certificate("old")],
  },
  claim_ids: ["claim-1"],
  email_attribute: "email",
  name_attribute: null,
  create_people: true,
  new_person_role: "coder",
  required: true,
  break_glass: ["admin-1"],
  mfa_context: null,
};

describe("single sign-on draft", () => {
  it("round-trips the saved version into the request it would save", () => {
    expect(requestFrom(draftFrom(SAVED))).toEqual({
      identity_provider: {
        entity_id: "https://idp.lakeside.example.com/saml",
        sso_url: "https://idp.lakeside.example.com/sso",
        certificates: ["old"],
        metadata_url: null,
      },
      claim_ids: ["claim-1"],
      email_attribute: "email",
      name_attribute: null,
      create_people: true,
      new_person_role: "coder",
      required: true,
      break_glass: ["admin-1"],
      mfa_context: null,
    });
  });

  it("keeps the current certificates when new metadata arrives so both are trusted during a rollover", () => {
    const imported = {
      entity_id: "https://idp.lakeside.example.com/new",
      sso_url: "https://idp.lakeside.example.com/sso2",
      metadata_url: "https://idp.lakeside.example.com/metadata.xml",
      certificates: [certificate("old"), certificate("new")],
    };
    const merged = withImported(draftFrom(SAVED), imported);
    expect(merged.provider?.entity_id).toBe("https://idp.lakeside.example.com/new");
    expect(merged.provider?.certificates.map((item) => item.value)).toEqual(["old", "new"]);
    expect(withoutCertificate(merged, "old").provider?.certificates.map((item) => item.value)).toEqual(["new"]);
  });

  it("has nothing to save without an identity provider and trims blank names to nothing", () => {
    const empty = draftFrom(null);
    expect(requestFrom(empty)).toBeNull();
    const draft = { ...draftFrom(SAVED), emailAttribute: "  ", mfaContext: " urn:mfa ", required: false };
    const body = requestFrom(draft);
    expect([body?.email_attribute, body?.mfa_context, body?.break_glass]).toEqual([null, "urn:mfa", []]);
  });

  it("adds and removes ids without duplicates", () => {
    expect(toggled(["a"], "a", true)).toEqual(["a"]);
    expect(toggled(["a", "b"], "a", false)).toEqual(["b"]);
  });
});
