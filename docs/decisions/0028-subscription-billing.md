# 0028 Subscription billing with Stripe and PayPal

Date: 2026-11-27

Context: since [0026](0026-self-serve-sign-up.md) a practice can start a trial on its own, but only HQ
could turn a trial into a paid plan, by editing the plan and renewal date by hand. The owner wants
practices to choose a plan and pay online, by card or PayPal, without HQ.

## Plans

One immutable catalog, `services/plans.py` (`CATALOG`), holds every plan, its display price in cents and
its limits. Prices are the owner's proposal and change only there and in the processors' price objects.

| Plan | Price | Users | Active providers | Bought online |
|---|---|---|---|---|
| `trial` | free for `TRIAL_DAYS` (14) | 5 | 2 | no |
| `essentials` | $149 per active provider a month, or $1,490 a year | 5 | 3 | yes |
| `professional` | $249 per active provider a month, or $2,490 a year | unlimited | 50 | yes |
| `enterprise` | custom, through sales (the demo-request flow) | unlimited | unlimited | no |

- **Per active provider.** A practice's cost tracks the clinicians whose notes it reviews, which is what
  drives the model and review work; seats would penalise a practice for giving its coders, billers and
  compliance staff their own accounts. The billed quantity is `max(1, active providers)`.
- **No feature gating.** Every plan has every feature; plans differ by price and limits only, so a
  limit is the only thing a plan can refuse (`services/plan_limits.py`: 409 naming the plan and limit
  on invite, unblock, provider add, reactivation and CSV import).
- **Annual is ten months.** The yearly price is ten times the monthly one; `annual_months_free` (2)
  is computed from the catalog, never typed.
- The old `basic` plan becomes `essentials` (migration 0009).

## Processors

- **Stripe** (official `stripe` SDK, async through httpx) with Stripe Checkout in subscription mode and
  the Stripe Billing Portal; **PayPal** through its REST API with httpx (no PayPal SDK). The browser is
  redirected to the processor's own page, so no card data and no processor script touch Bodha
  (`frontend` needs no new dependency).
- Each processor is an adapter behind one contract (`adapters/billing_contract.py`: checkout link,
  manage link, cancel at period end, set quantity, read a verified webhook, fetch a subscription), so a
  third processor is one more adapter.
- A processor is offered only when its credentials (`adapters/billing_providers.py`) and all four price
  ids (`plans.prices_complete`) are set; `GET /api/plans` lists the offered ones.
- PayPal has no "cancel at period end": cancelling stops future payments at once, and Bodha keeps
  access to the last paid day it stored. PayPal also has no portal: the manage link is the payer's
  automatic payments page.

## Webhooks are the only source of subscription state

The browser return (`/plan?checkout=done`) never changes anything. Every Stripe and PayPal event is
verified (Stripe: `Stripe-Signature` HMAC over the raw body, five-minute tolerance; PayPal:
`/v1/notifications/verify-webhook-signature` with `PAYPAL_WEBHOOK_ID`), recorded once in
`billing_events` (primary key provider and event id, inserted with `ON CONFLICT DO NOTHING` in the same
transaction as its effect, so a repeat is a no-op and a failure is retried), and then the subscription
is fetched from the processor rather than read from the event, so events arriving out of order cannot
move the state backwards. One `subscriptions` row per practice holds the current state; HQ activity
`subscription changed` keeps the history.

| Processor state | Stored | Practice |
|---|---|---|
| Stripe `active`, `trialing`; PayPal `ACTIVE` | `active` | status `active`, plan from the price, `renews_on` = the period's last day in the practice's time zone |
| Stripe `past_due`, `unpaid`, `paused`; PayPal `SUSPENDED`; a failed payment on an active subscription | `past_due` | access until `past_due_since` + `BILLING_GRACE_DAYS` (7); admins see a banner |
| Stripe `canceled`; PayPal `CANCELLED` | `canceled` | after a live subscription: access to the period end (or the grace end if it was past due), then the plan has ended (billing-only access, below) |
| Stripe `incomplete_expired`; PayPal `EXPIRED` | `expired` | as canceled |
| Stripe `incomplete`; PayPal `APPROVAL_PENDING`, `APPROVED` | `pending` | unchanged; a checkout that never paid leaves a trial alone |

- A webhook never lifts an HQ block and never reopens a practice HQ ended.
- An event for another subscription replaces the stored one only when it is live, or the stored one is
  not, so a late event for an old subscription cannot overwrite a new one.
- An event whose price no plan uses is logged as an error and skipped rather than retried for days.

## HQ override rule

HQ can still create practices on any plan and set plan, seats and renewal by hand as a comp or an
invoice arrangement. While a paid subscription is live (`active` or `past_due`) the subscription wins:
HQ's change of plan or renewal date, and HQ renew, answer 409 naming the processor; seats, status (block)
and name stay HQ's. Seats cap users only for a practice without a live subscription (and never above the
plan's user limit); a paying practice follows its plan. A practice with a live subscription cannot be
deleted until the subscription ends.

## Quantity follows the providers

Adding, reactivating, retiring or importing providers schedules a background sync for the practice; the
worker also sweeps every live subscription every 15 minutes. Stripe updates the subscription item with
`proration_behavior=create_prorations`; PayPal revises the subscription quantity. A failure is logged
and left for the next sweep; it never blocks the admin. A PayPal revision that needs the payer's
approval is treated as a failure.

## Billing-only access after the plan ends

A practice's plan has ended when `renews_on` is before today in its time zone: a trial that ran out, a
paid period that passed, or a subscription that ended after its period. Its admins could otherwise
never reach `/plan` to pay, so they get a billing-only session instead of the `PlanEnded` refusal.

- **Derived on every request, never stored.** `core.deps.ensure_session_allowed(user, practice)` is the
  one rule for sign-in (password, Google, Microsoft, Yahoo, two-step, refresh) and every authenticated
  request: HQ passes; a practice that is not `trial` or `active` (HQ blocked or ended it) answers 401
  "your practice is not active", so an HQ block always wins; a plan that has ended answers 403
  `PlanEnded` to every role except `PLAN_MANAGERS` (`core.roles`, the admins). Nothing marks the token,
  so the next request after a webhook moves `renews_on` forward is a full session again, and an admin
  already signed in when the plan ends drops to billing-only on the next request.
- **One guard.** `session_actor` resolves the signed-in user and records `billing_only_since` (the day
  the plan ended) on the `Actor`; `current_actor`, which every `require(*roles)` guard and every other
  route depends on, refuses that actor with `PlanEnded`, so a new route is closed to billing-only
  sessions unless it opts in. Only these opt in, through `session_actor` or `require_for_billing(*roles)`:
  `GET /api/auth/me`, the signed-in devices and recovery codes routes, `GET /api/plan`,
  `POST /api/plan/checkout`, `/portal` and `/cancel`. Routes with no session (`GET /api/plans`, sign-in,
  refresh, sign-out, two-step, password and webhooks) are unchanged. A test lists every route that
  accepts a billing-only session.
- **The client follows the session.** `User.billing_only` comes with every sign-in, refresh and
  `GET /api/auth/me`. While it is true the practice layout sends every page to `/plan`, the sidebar shows
  only Plan and billing with the account and sign out, search is off, and `/plan` says the plan has
  ended above the choose-plan flow; the plan standing is `ended` when no subscription explains it. After
  `/plan?checkout=done` the screen reloads the plan and renews the session every four seconds, up to
  five times, until the webhook has made the session full again.

## No PHI to processors

Only the admin's email, the practice id (Stripe `client_reference_id` and metadata, PayPal `custom_id`),
the plan and interval and the provider count leave Bodha. Errors from processors are logged by type
only; secrets are `SecretStr` and never logged.

## Follows

- Other roles of a practice whose plan has ended still cannot sign in (`plan_ended`), and see the
  existing message until an admin pays.
- Production needs the settings and processor setup in [DEPLOY.md](../DEPLOY.md#set-up-stripe-and-paypal);
  infra is changed separately.
