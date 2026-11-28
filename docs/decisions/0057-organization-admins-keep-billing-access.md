# 0057 Organization admins keep billing access after their organization's plan ends

Date: 2026-11-28

Context: a session belongs to one practice. Once a plan ends, `ensure_session_allowed` allowed only the
practice's admins in, as a billing-only session. An organization admin pays for combined practices from
the organization's plan page, but may hold only a coder or viewer membership in those practices (0044).
When the organization's plan ended, that person could not sign in at all, so only HQ could renew. The
owner chose to loosen the rule.

## Choice

- `core.deps.ensure_practice_open(db, user, role, practice)` replaces `ensure_session_allowed`. After the
  plan ends it also lets in an active admin of the practice's organization (`pays_for`). That costs one
  query, run only once the plan has ended. The session is billing-only exactly as for a practice admin:
  `current_actor` still refuses every working route, so no practice records open.
- The organization's plan routes already accept a billing-only session (`BillingAdmin`). Such a session
  for a person who is not a practice admin now lands on its organization's plan page (`homeFor`), which
  `canOpenPath` already allowed. The practice plan page is not offered to that person.
- Login, refresh, the two-step step, practice switching and every request use the same check.
