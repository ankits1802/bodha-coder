# 0061 SAML 2.0 single sign-on for practices and organizations

Date: 2026-11-28

Context: larger groups want their people to sign in through their own identity provider (Okta, Entra ID,
Google Workspace, ADFS and others), and to stop password and social sign-in for their staff. Bodha
already proves who owns an email domain (0044: DNS TXT or an admin mailbox, one verified claim per
domain) and already has one sign-in policy (`services.auth.sign_in_user`).

## Choice

### Who configures what

- A practice admin configures single sign-on for the practice (`/api/practice/sso`), an organization
  admin for the organization (`/api/organizations/{id}/sso`), which then covers the organization's
  practices. HQ cannot: the routes are behind the practice and organization guards, and the SAML routes
  answer only on the practice realm's host.
- A configuration is an `sso_connections` row (its id is fixed, so the entity ID and ACS URL given to the
  identity provider never change) and one `sso_versions` row per save. Versions are append-only in the
  database; a connection row is written once and can only be marked removed. The newest version is the
  one in force.
- The domains a configuration covers are verified, unreleased domain claims of the same owner, stored by
  claim id. A domain reaches at most one configuration because a domain has at most one verified claim.
  Releasing the claim, closing the practice or organization, or removing the connection ends single
  sign-on for that domain at once (`services.sso_policy.route_for_email`).

### Library

- [signxml](https://github.com/XML-Security/signxml) 5.3.1 on lxml 6.2.0 and the existing cryptography.
  Both are pure Python or ship manylinux wheels for Python 3.14, so the slim Docker image and GitHub's
  runners need no system packages. python3-saml (python-xmlsec, libxmlsec1) and pysaml2 (the xmlsec1
  binary) were refused for their system dependencies.
- signxml verifies XML signatures only; every SAML rule is Bodha's own code in `adapters/saml_*.py`,
  tested with an identity provider faked from keys generated in the tests (`tests/saml_idp.py`).

### Verification (adapters/saml_response.py)

- The response is base64 at most 1.4 MB, parsed by lxml with entity resolution, DTD loading and the
  network off, and refused if it holds a document type declaration or an entity at all.
- The status must be Success. Encrypted assertions are refused. The response must hold exactly one
  `Assertion`, as a direct child; no ID value may repeat; a `ds:Signature` may sit only directly under the
  response or the assertion, one each.
- At least one of the two is signed. Each present signature is verified against the pinned certificates
  only (any certificate in `KeyInfo` is ignored), with one reference, SHA-1 refused, and the signed
  element must be the response or assertion it sits in, with the same ID. Every value Bodha reads comes
  from signxml's re-parsed signed element, never from the received tree, so comments or wrapped copies
  cannot change what is read. A pinned certificate past its validity date no longer verifies.
- Checked with two minutes of skew: response `Destination` (when present) and the bearer
  `SubjectConfirmationData` `Recipient` equal the ACS URL; the issuer (assertion, and response when
  present) equals the configured entity ID; every `AudienceRestriction` names Bodha's entity ID;
  `NotBefore`/`NotOnOrAfter` on the confirmation and the conditions; `IssueInstant` at most ten minutes
  old; `SessionNotOnOrAfter` in the future; `InResponseTo` equal to the request this browser started, or
  absent for an unsolicited response.
- Replays: the SHA-256 of issuer and assertion ID is stored in `sso_assertions` with a unique index when
  the assertion is used, with the time it expires. The runtime role cannot delete, so ids are kept for
  good, which is stricter than keeping them until they expire.
- The email comes from the configured attribute or else the NameID, and must belong to one of the
  configuration's live domains; otherwise the sign-in is refused (`sso_domain`).
- Nothing from an assertion is logged; `signxml` is a quiet logger; errors carry only a reason code.

### Requests, RelayState and IdP-initiated sign-in

- SP-initiated: `GET /api/auth/saml/{id}/start` sends an unsigned `AuthnRequest` with the HTTP-Redirect
  binding (metadata without that binding is refused), a 16-character random RelayState, and a signed
  ten-minute cookie `bodha_saml` (request id, RelayState, next path) on the path
  `/api/auth/saml/{id}`, SameSite=None and Secure because the identity provider posts to the ACS from
  another site. The ACS requires the cookie's request id in `InResponseTo` and the same RelayState.
- The next page is kept only when it is a same-site path (`/` then no `/` or `\`, safe characters, not
  under `/api/`), both on the server and on the sign-in page.
- IdP-initiated: an unsolicited response is verified and consumed like any other, then never signs
  anyone in; Bodha answers by starting its own SP-initiated sign-in (the identity provider's session
  makes it seamless). A replayed or forged unsolicited response therefore cannot create a session, and
  login CSRF needs the victim's own identity provider session.
- No signing or encryption certificate is published: requests are unsigned and encrypted assertions are
  refused; transport is TLS.

### Policy

- Required mode refuses password sign-in (403 `sso_required`), Google, Microsoft and Yahoo sign-in,
  forgot-password emails, set-password links and email sign-up for the covered domains; invitations say
  to sign in with single sign-on. Break-glass admins listed in the version keep password sign-in, and
  Bodha's two-step is then always asked. Required mode needs at least one break-glass admin who has a
  password and two-step on, so a broken identity provider cannot lock everyone out. If every
  break-glass admin is lost, support runs `python -m app.scripts.lift_sso_requirement` (OPERATIONS),
  which appends a version with required off, recorded as Bodha support.
- New people are created only when the version allows it, never as admins, in the practice the domain
  claim names, within the seat limit; otherwise `no_account` or `no_seat`.
- A session after single sign-on is an ordinary session (refresh, idle time-out, practice rules). Bodha's
  two-step is skipped only when the assertion's `AuthnContextClassRef` equals the version's configured
  value; such a session carries `sessions.idp_two_step` so refresh and practice switches accept it for
  roles that need two-step. Otherwise `sign_in_user` decides as for any sign-in.
- SAML identities are not bound in `user_identities`: the domain owner's identity provider is
  authoritative for its domain, and binding the NameID would lock people out when the group changes
  identity provider.

### Records

- Changes (`sso_changed`), tests (`sso_tested`), SSO sign-ins (`signed_in` "with single sign-on") and
  refusals (`sign_in_failed` "single sign-on: <reason>") are auth events and access-log entries of the
  owner's practices; refusals for an unknown person are system entries with the reason only.

## Consequences

- Tried only against the faked identity provider; Okta, Entra ID, Google Workspace and ADFS still need a
  real test before a customer relies on required mode.
- An identity provider that only offers HTTP-POST for requests, signs with SHA-1, or encrypts
  assertions is refused, with the reason shown in Test sign-in.
