# 0040 Electronic signatures and sealed records

Date: 2026-11-28

Context: an approval, a compliance decision and a provider's addendum or level statement were stored as
records, but nothing tied them to the person's own signature, and nothing showed an auditor that a record
had not changed since it was signed. ChartMate already captures signatures (draw, upload, a Gemini check,
preview, accept). The owner asked for the same on Bodha's notes, with a digital fingerprint.

## Choice

- **Capture, reused from ChartMate.** A person with a role that decides (admin, coder, CDI, compliance)
  adopts a signature once on Security: drawn on a pad (pointer events, so mouse, pen and touch), typed as
  their full name and drawn by the browser in the system script font, or a photo resized to PNG in the
  browser. The server accepts a PNG data URL only (24 to 2400 pixels a side, 1.5 MB, decoded fully before
  it is kept). A drawn or photographed image is checked by Gemini (`ai/signature_check.py`): one
  handwritten signature, nothing else written, not several; a refusal is a 422 with the reason and nothing
  is stored. Without the check (Gemini unreachable or not set up) a drawn or uploaded signature waits with a
  503 and typing still works; a typed signature needs no image check because it is drawn from the typed
  name. The verdict, the model and the check version are kept on the signature row. `GEMINI_BACKEND=demo`
  answers a fixed passing verdict. ChartMate's Pillow clean-up and crop are not ported: the browser crops
  drawn strokes and resizes photos, and Bodha does not add Pillow as a direct dependency.
- **Records, never edits.** `signatures` holds each captured image (owner, source, typed name, SHA-256,
  size, check, address, device); `signature_adoptions` records each adoption; the latest adoption is the
  person's signature. Replacing one adds an adoption and keeps the earlier signature. Drafts that were never
  adopted stay as records of the attempt. Images live under `people/{user}/signatures/{id}.png` (one
  signature per person across practices) and `practices/{practice}/signatures/{id}.png` for providers.
- **Providers sign on the secure link.** `POST /api/respond/signature/drafts` captures the provider's
  signature (same check); the answer or level statement carries `signature_id`, or none to use the
  signature the provider asked Bodha to remember for that practice (`remember_signature`). Without either
  the answer is refused with `signature_required`.
- **Signing on approval, without an extra click.** `approve`, bulk approve and compliance confirm or keep
  read the approver's adopted signature and apply it; without one they answer 409 `signature_required`
  before anything is written. The web client opens the capture dialog on that answer, waits, and repeats the
  same request once the signature is adopted (`useSignatureGate`), so the keyboard shortcut and Approve all
  keep working and later approvals cost no extra request. Auto-approvals have no signer and are not sealed.
- **Envelope and seal.** Each signing event writes one `signing_events` row whose `envelope` is canonical
  JSON (keys sorted, no whitespace, UTF-8, no floating point numbers; version 1): event, practice, note,
  record id, the statement adopted, signer kind, id, name, role or credential and typed name, the signature
  image SHA-256, the document SHA-256 (`notes.file_sha256`, the SHA-256 of the PDF bytes at upload), the
  SHA-256 of the canonical source record (the approved claim snapshot, the provider statement, or the
  practice's agreement record), the time in UTC to the microsecond, the address and the device. The
  envelope's SHA-256 is signed with AWS KMS `Sign` (`ECDSA_SHA_256`, `MessageType=DIGEST`) on the
  `ECC_NIST_P256` key named by `SIGNING_KEY_ID`; the DER signature, the key ARN KMS returns and the
  algorithm are stored. A KMS failure fails the approval (503), so no unsealed approval exists.
- **Development key, kept apart.** `adapters/development_signer.py` derives one fixed P-256 key from a
  constant and seals as key id `development`. `build_record_signer` uses it only when `SIGNING_KEY_ID` is
  unset and `APP_ENVIRONMENT` is not production; in production the API refuses to start without the key.
  The KMS verifier never accepts a development seal, and the development verifier never accepts a KMS one.
- **Verification.** `GET /api/verify/{code}` (public, 30 a quarter hour per address) finds the event by its
  verification code (twelve letters from an alphabet without 0, 1, I, L, O or U), recomputes the source
  record's SHA-256 from the stored record, re-reads the signature image and hashes it, rebuilds the envelope
  from the row and checks the seal with the public key (`GetPublicKey`, cached per key in the signer
  object). It answers valid or the list of what no longer matches, with the event, practice name, signer
  name and role, time and the two fingerprints only. `/verify` shows the result; a PDF chosen there is
  hashed in the browser with Web Crypto and compared with the document fingerprint, so the document never
  leaves the device.
- **Certificates.** Every defense packet ends with a "Certificate of review" page per signing event of the
  note, and the audit package adds `certificates/{code}.pdf` and `signing-events.json` (envelopes and
  seals, for checking offline). A certificate shows the signed content, the signature image, the signer,
  time, address, device, the three fingerprints, the seal and the verification address.
- **Agreement at sign-up.** Self sign-up by email or by a sign-in service seals the agreement record the
  practice keeps (version, time, method, address) with the new admin's typed name and no image. Starting a
  second practice from an existing account is not sealed yet.
- **Database guard.** The three tables carry the audit hardening's `bodha_reject_change` triggers for
  UPDATE, DELETE and TRUNCATE and `bodha_stamp` on `created_at`; `signed_at` is never stamped because it is
  part of the envelope. The runtime role may only select and insert. `bodha_purge_practice` removes signing
  events, adoptions and signatures of a purged practice, and of people who belonged only to it, before
  notes, providers and users; the purge then removes those people's stored images.

## Consequences

- Fingerprints prove that the stored records match what was signed; they do not prove the PDF in storage
  is the uploaded one unless it is hashed again, which the audit package and the verify page let anyone do.
- Rotating the signing key means a new KMS key: older events keep the key ARN they were sealed with and
  still verify while the app role may read that key's public key.
- Voiding a note keeps its signing events; they verify as long as their records exist.
- Tests and CI seal with the development key; the KMS path is tested with a stubbed client.
