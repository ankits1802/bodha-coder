# 0044 Organizations, combined billing and joining by email domain

Date: 2026-11-28

Context: a group with several locations ran each location as a separate practice with its own plan,
its own admins and no view across them, and a colleague who signed up with the group's work email got a
new trial practice instead of joining the one their colleagues already used. The owner wants a group
managed as one organization with one combined pool, and colleagues to join by their email domain.

## Organizations

- **One organization per practice.** `organizations` (name, `status` `active`, `closed`, `purged`, the
  combined `plan` and `renews_on`, `closed_at`, `closed_by`, `purged_at`) and `practices.organization_id`.
  HQ creates an organization (`POST /api/hq/organizations`, a trial plan ends after `TRIAL_DAYS` in UTC),
  attaches and detaches practices (409 for a practice that belongs to another organization or is closed),
  renames it and changes its plan.
- **Organization admins are not practice roles.** `organization_memberships` (person, organization, `role`
  `admin`, `added_by`, `ended_at`; unique per person and organization; `realm` fixed to `practice` and
  joined to `users (id, realm)` like `practice_memberships`, so an HQ account can never hold one). HQ adds
  an existing practice account by email with a reason (`POST /api/hq/organizations/{id}/admins`, 404 for an
  email without a practice account) and removes one; both write HQ activity. A person signs in through a
  practice membership as before; `user.organizations` (practice accounts only) lists the organizations
  they administer and every organization route checks the membership again (404 otherwise, also for HQ).
- **No PHI without a membership.** Being an organization admin opens the organization's pages only:
  practice names, statuses, plans, user and active-provider counts, combined insights (per practice:
  notes read, approved, on time, outcomes and the Medicare estimate difference; no patient, note or
  provider rows) and the combined plan. Opening a practice still needs an active practice membership; the
  switch refuses one the person does not hold (403). `POST /api/organizations/{id}/practices/{pid}/access
  {role, reason}` gives the caller a membership: refused while they have a live membership there (a
  practice admin's block or removal stays theirs to decide until the membership ends), within the plan's
  users and seats, recorded as `access granted by organization admin` with the role and reason in that
  practice's access log and in HQ activity, and emailed to the practice's other active admins without the
  reason.
- **Adding people across practices** (`POST /api/organizations/{id}/people {name, email, practices:
  [{practice_id, role}]}`) reuses the 0037 enrolment: an existing practice account gets the memberships
  and one "You've been added to A, B" email, a new email an invited account and one set-password invite
  naming the organization; every practice is checked for room first and a live membership in any of them
  refuses the whole request (409). Each practice's access log records `member invited` or `member added`
  with the organization's name.
- **New locations.** `POST /api/organizations/{id}/practices {name, time_zone, agreed}` creates a practice
  in the organization and in combined billing with the organization's plan and renewal, the creator as its
  first admin, `practices.signup.source` `organization` with the agreement acceptance, and writes
  `practice added by organization` to HQ activity and the new practice's access log.

## Combined billing

- **The organization's terms are copied onto its combined practices.** `practices.combined_billing` (a
  check keeps it false outside an organization). Joining copies the organization's plan and renewal (or,
  while the organization's subscription is live, the subscription's plan and the period end in the
  practice's own time zone) onto the practice; every change of the organization's terms copies them again
  (`organization_billing.follow_all`). Copying was chosen over reading the organization on every request
  so that `ensure_session_allowed`, `plan_ended_on`, billing-only sessions, plan limits, digests and the
  HQ practices list keep their one rule each: a combined practice whose organization's plan ended is a
  practice whose plan ended. A practice HQ ended or blocked is never reopened by the organization, as a
  webhook never lifts an HQ block. Leaving combined billing keeps the copied terms, so the practice keeps
  the period the organization paid for and then pays on its own.
- **Joining is refused** for a closed practice, a practice with its own live subscription (cancel it
  first, so nobody pays twice) and a practice over the organization plan's per-practice limits. HQ and the
  organization's admins move practices in and out (`PUT .../practices/{pid}/billing {combined}`); each
  move writes `combined billing joined` or `left` to HQ activity and schedules a quantity sync.
- **One subscription per organization.** `subscriptions.organization_id` (unique) beside `practice_id`,
  exactly one set. `POST /api/organizations/{id}/plan/checkout` (with portal and cancel) starts Stripe or
  PayPal like a practice checkout: quantity `max(1, active providers in the combined practices)`, refused
  with no combined practice or with one over the plan's provider limit, returning to
  `/organizations/{id}/plan`. The processors carry the owner: Stripe metadata `organization_id` (and
  `client_reference_id`), PayPal `custom_id` `organization:<id>`; `ProcessorSubscription.organization_id`
  reads it back. Webhooks fetch the subscription as before and, for an organization, update its row, its
  plan and renewal (UTC) and every combined practice; a payment failure tells each combined practice's
  admins. The quantity sync counts the combined practices' active providers for an organization row, and
  a provider change in a combined practice syncs the organization's subscription.
- **Plan limits stay per practice**, from the copied plan: users and active providers are counted in each
  practice against the organization plan's limits; seats cap users only while neither the practice nor its
  organization has a live subscription (`plan_limits.governing_subscription`).
- **The practice's plan page** answers the organization's subscription and standing with
  `organization {id, name}`; checkout from the practice is refused (409) and the page links an
  organization admin to the organization's plan. HQ cannot change the plan or renewal of a combined
  practice (409, change the organization) nor close one (take it out first). HQ renews an organization by
  hand like a practice (`POST /api/hq/organizations/{id}/renew`, refused while its subscription is live).
- **Billing-only through the organization**: the organization plan routes accept a billing-only session
  (`session_actor`) of an organization admin, as `/api/plan` does for practice admins.

## Join by work email domain

- **Claims.** `domain_claims` (domain, the practice people join, the organization when an organization
  admin made the claim, who claimed, a random token, the emailed link's hash, address and expiry,
  `verified_at` and `verified_via` `dns` or `email`, `join_mode` `off`, `request` or `auto`, `join_role`,
  `released_at`). A practice admin claims for their practice (`/api/practice/domains`), an organization
  admin for any of its practices (`/api/organizations/{id}/domains`). Domains are lowercase ASCII (IDN as
  `xn--`); public email services (`services.email_domains.PUBLIC_EMAIL_DOMAINS`, their subdomains
  included) are refused (422). Several practices may claim a domain but only one claim per domain can be
  verified and unreleased (a partial unique index; verifying a held domain answers 409).
- **Verification.** DNS: a TXT record `bodha-verify=<token>` on the domain, read through
  `adapters.dns_txt.TxtResolver` (`DnsTxtResolver` uses dnspython's resolver with the system's DNS servers;
  tests use a fake), 10 checks an hour per claim. Email: a link to one of the mailboxes certificate
  authorities accept for domain control (`admin`, `administrator`, `hostmaster`, `postmaster`,
  `webmaster`), 3 an hour per claim, valid 72 hours, single use; the page `/verify-domain` confirms only
  when the reader presses Confirm, so link scanners do not verify a domain. dnspython was already installed
  as a dependency of email-validator; it is now declared directly at the same pinned version.
- **Joining.** Once verified, an admin chooses off (the default), "ask to join" or "join automatically"
  with a role (viewer suggested; never admin). A sign-up whose email domain has an open claim on an open
  practice is offered that practice:
  - Email sign-up keeps answering the same for every email. In the background, instead of creating a
    practice, it emails a signed 72-hour link (`/sign-up/join#<token>`, never in a query string) offering
    "Join <practice>" or "Start <their practice>", so the practice's name is shown only to someone who
    holds the address. `POST /api/signup/join {token, join}` then requests to join, joins (an invited
    account and membership, and the set-password invite) or starts the trial practice as before.
  - A sign-in service sign-up shows the offer on `/sign-up/practice` (`PendingIdentity.join`), the email
    being verified by the service; `POST /api/signup/identity/join {name}` joins and signs in, or answers
    `{outcome: "requested"}`.
  - An automatic join into a practice with no room for another user becomes a request.
- **Requests and approvals.** `domain_join_requests` holds every request (`pending`, `approved`,
  `declined`) and every automatic join (`joined`) with the claim, practice, name, email, role, the
  account and who decided. A request tells the practice's admins in their inbox (kind `join_requested`,
  payload `request_id`, the requester's name as the actor); admins approve with a role from Team (the 0037
  invite, which emails the person) or decline. Deciding marks the inbox items of the request read.
- **Audit.** Claiming, sending the verification email, verifying, changing the join setting and releasing
  are written to the target practice's access log and HQ activity; an email verification names the
  mailbox as a system actor; requests and automatic joins are written by `Bodha (email domain)`;
  approvals and declines by the admin.

## Retention and the database

- Migration 0019 adds the tables with database `created_at` (`clock_timestamp()`, stamped by
  `bodha_stamp`), `bodha_no_delete` and `bodha_no_truncate` on all four, and `bodha_closure` on
  `organizations` (added open, closing final, only the purge marks it purged). The runtime role gets
  SELECT, INSERT and UPDATE on the four tables and EXECUTE on `bodha_purge_organization`; no DELETE.
- **Closing an organization** (`POST /api/hq/organizations/{id}/close {confirm_name}`, refused while its
  subscription is live) takes every practice out of combined billing and the organization, releases its
  claims and ends its admin memberships; the practices and all their records stay.
- **Purging an organization** (`.../purge`) is refused until `RETENTION_DAYS` after `closed_at` by the
  database clock, mirroring practices: `bodha_purge_organization` deletes its claims' join requests, its
  claims, its subscription and its memberships, and the accounts of people who belong to no practice and
  no other organization (their tokens, codes, identities, sessions, sign-in events and personal
  signatures), and marks the row `purged`. It deletes nothing of any practice.
- `bodha_purge_practice` (patched from its current definition, as 0017 did) deletes the practice's join
  requests and domain claims before its subscription, and keeps the account of a person who is an
  organization admin even when the purged practice was their only one.
- The downgrade refuses while any organization, domain claim or join request notice exists.

## Follows

- Rolling deploy: the release before 0019 lists every subscription; an organization's row has no
  `practice_id`, and its quantity sweep would count no providers for it. Organization checkouts are only
  possible on this release, so the window is the deploy itself.
- HQ activity has no organization column: organization events name the organization in their detail;
  adding a column would leave it outside the activity hash chain until a new content version.
- An organization admin who holds no admin membership in any combined practice cannot sign in once the
  organization's plan has ended (non-admin roles are refused as before); HQ can renew the organization.
- Production SES must be able to deliver to the domain's admin mailboxes; the API's tasks resolve TXT
  records through the VPC resolver.
