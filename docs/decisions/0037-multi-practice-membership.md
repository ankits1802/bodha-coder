# 0037 One person, several practices

Date: 2026-11-28

Context: a user carried one `practice_id` and one `role`, so a coder or consultant working for several
clients, or a billing company, needed a separate email for each practice. Practice admins had no way to
add someone who already had an account ("someone already uses that email"), self sign-up refused an
email with an account, and an audit review asked for a durable record of authentication events.

## Choice

- **Memberships.** `practice_memberships` holds one row per person per practice (unique
  `(user_id, practice_id)`): `role`, `status` (`invited`, `active`, `blocked`), `invited_by`,
  `created_at`, `ended_at`. A removal or a leave sets `ended_at`; rows are never deleted except with
  their practice. `realm` is fixed to `practice` by a check and joins `users (id, realm)` through a
  foreign key, so an HQ account can never hold a membership. The person's identity stays on `users`:
  email, name, password, two-step, sign-in service links, sessions, `users.status` (`invited` until a
  password or a sign-in service is first used, `active`; `blocked` is now used only by HQ accounts and
  by practice accounts blocked before this change). HQ users keep their realm and role.
- **The active practice lives in the session.** The access token carries `prc` (practice id) and
  `rol` (the membership role when it was issued); `sessions.practice_id` remembers it for refresh.
  Every request (`core.deps.session_actor` through `practice_access`) re-reads the membership: it must
  be `active` and not ended, the practice must allow the session (`ensure_session_allowed(role,
  practice)`, so plan-ended and billing-only rules apply per practice and per membership role), and the
  role must still equal `rol`. A changed role answers 401 once, the client refreshes, and the new token
  carries the new role; a block or removal answers 401 and the refresh is refused. `Actor.role` is the
  membership role (`hq` for HQ users) and every role guard reads it.
- **Two-step per practice.** `needs_two_step(access)` is HQ, or the membership role in the active
  practice's `mfa_roles`. Sign-in, refresh and a switch apply it to the practice being entered; a switch
  into a practice that needs two-step from someone who has none answers the setup challenge for that
  practice instead of a session. A refresh is refused when the practice now needs two-step and the person
  has none, so a new role or a new practice rule takes effect at the next refresh.
- **Landing and switching.** Sign-in lands on `users.last_practice_id` when that membership is active
  and the practice allows the session, otherwise on the oldest membership that does; when none does,
  the refusal of the preferred practice is returned (practice not active, or plan ended). `POST
  /api/auth/practice {practice_id}` needs the caller's own refresh cookie, refuses (403) a practice the
  person is not an active member of or one that is not open, rotates the refresh token, moves the session
  and writes `practice switched` to the auth events and the entered practice's access log. The other
  practice is never named in a practice's log.
- **Invites.** Inviting an email that already has a practice account adds a membership (`active` for an
  active person) and emails "You've been added to <practice>" with a sign-in link; a new email gets the
  set-password invite as before, and its memberships become `active` (`invite accepted` in each practice's
  log) when the password is set or a sign-in service is first used. Seats and plan limits count the
  practice's live memberships that are `invited` or `active`, as invited users counted before, so a
  practice cannot invite past its seats.
- **Admins manage memberships only in their own practice**: change role, block, unblock, remove (`DELETE
  /api/team/{user_id}`). A block or a removal ends the person's sessions in that practice only; their
  other practices are untouched. An admin of one practice may not reset the two-step of someone who also
  belongs to another practice (409); that person uses a recovery code, or support resets it.
- **Last active admin.** Demoting, blocking, removing or leaving is refused (409 "a practice needs at least
  one active admin") when it would leave the practice without an `active` admin membership; the check
  locks the practice's active admin rows so two simultaneous changes cannot both pass. An invited admin
  does not count.
- **Leaving.** `POST /api/auth/practices/{id}/leave` from the account page ends the caller's membership
  (`member left`); leaving the practice the session is in signs the person out, and the next sign-in lands
  on a practice they still belong to.
- **Self sign-up with an existing account.** The email form keeps answering the same for every email; an
  existing account gets an email asking to sign in, with a link to `/sign-in?next=/practices/new`. Signed
  in, `POST /api/auth/practices` creates the trial practice with the caller as its first admin and
  switches the session into it (`practices.signup.method` `account`). A sign-in service started from the
  sign-up page (`intent=signup`) always goes to the sign-up form; completing it for an existing account
  signs that account in through the service and makes it the new practice's admin.
- **HQ appoints an admin** (`POST /api/hq/practices/{id}/admins {name, email, reason}`): an existing
  practice account gets an admin membership (or an existing member is made admin, unblocked if needed), a
  new email gets an admin invite. The practice's other active admins are emailed that HQ added an admin.
  HQ activity and the practice access log both record `admin appointed by HQ` with the person and the
  reason HQ typed (required, 3 to 200 characters).
- **Where membership changes are recorded.** Practice admins' membership changes (`member invited`,
  `member added`, `member role changed`, `member blocked`, `member unblocked`, `member removed`) and the
  person's own (`invite accepted`, `member left`, `practice switched`) go to the practice's access log; HQ
  activity records them only when HQ acts. They no longer go to HQ activity when a practice admin acts.
- **Auth events.** `auth_events` is append-only: kind, realm, user id when known, practice id when known,
  a SHA-256 hash of the lowercased email for failed sign-ins, IP, user agent and a short detail; never an
  email, password, code or token. Kinds: failed sign-ins (wrong password, unknown email, wrong two-step or
  recovery code, a refused sign-in service), sign-ins, a password set from an invite link
  (`password_set`) or a reset link (`password_changed`), two-step on and off, recovery codes replaced and
  used, sign-outs, ended sessions and practice switches. Each event is also shown where people look:
  an HQ account's events in HQ activity (now with the address, which HQ sign-ins lacked), a practice
  account's events in the access log of the practice they name, or, when they name none, of every
  practice the person currently belongs to. An unknown email has no practice to show it to and stays in
  `auth_events` only. Practice events follow the practice's access-log retention; events without a
  practice are kept six years. Replaced recovery codes are now marked used instead of deleted.

## Rolling deploy

Migration 0014 must work with the release before it, which still reads `users.practice_id`, `users.role`
and `users.status`.

- The columns stay. Removing `users.role` would break every query of the release before (and
  `users.realm` is computed from it); `users.practice_id` is read by that release on every request. The
  new code never reads them for practice access: the model calls the column `legacy_practice_id`, new
  practice accounts are created with it empty (so the release before refuses them instead of guessing),
  and every membership change empties it for that person, so the release before refuses them rather than
  act on a role or practice that has changed. `users.role` is written once when an account is created (the
  first membership's role, `hq` for HQ) and never read for practice access.
- Writes by the release before reach memberships through a trigger, `users_legacy_membership`: inserting
  a practice user with a `practice_id`, or changing the role or status of one whose `practice_id` is still
  set, upserts the matching membership (never reopening an ended one). New code never sets
  `practice_id`, so the trigger acts only on rows the release before wrote or has not been touched since.
- The upgrade copies each practice user into one membership with their current practice, role and
  status (`membership_for` in the migration) and sets `last_practice_id`. The downgrade refuses while
  anyone has more than one live membership, and otherwise writes each person's live membership back to
  `practice_id`, `role` and `status` (`legacy_columns`; blocked when either the person or the membership
  is blocked, detached when the membership ended).
- The release after this one removes them, as [DEPLOY.md](../DEPLOY.md#releases-migrations-first) asks:
  a migration drops the trigger and `users.practice_id`, turns `users.realm` into a plain column, and
  drops `users.role`.

## Follows

- Tokens issued before the deploy carry no `prc`: they answer 401 once and the client refreshes, which
  lands the session on a practice. Sessions created before the deploy have no `practice_id` and land the
  same way.
- The frontend's user carries `practices` (id, name, role of each active membership). The sidebar shows a
  practice switcher when there are two or more; a switch reloads the app on that practice's home, so no
  cached data of the previous practice survives. The account page (Security) lists the practices with
  role and Leave, and links to `/practices/new`.
- Deleting a practice deletes its memberships, its sessions and its auth events, and deletes only the
  people with no membership in any other practice.
