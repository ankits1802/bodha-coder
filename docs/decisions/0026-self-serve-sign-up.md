# 0026 Self-serve sign-up and more sign-in services

Date: 2026-11-27

Context: until now an HQ person created every practice (`services.hq.create_practice`) and invited its
first admin, and Google signed in only people who already had an account
([0008](0008-google-sign-in-and-recovery-codes.md), "No self sign-up"). The owner wants practices to
start a trial on their own so growth does not wait on HQ, and asked for Microsoft and Yahoo next to
Google. This record replaces the "No self sign-up" point of 0008.

## Choice

- **Two ways in, one result.** `POST /api/signup` (name, practice, work email, time zone, agreement)
  or a verified Microsoft, Google or Yahoo identity without an account. Both create a practice with
  status and plan `trial`, `TRIAL_SEATS` seats (5) and `renews_on` = today in the practice's time zone
  plus `TRIAL_DAYS` (14), and its first admin. Nothing else about the practice is special: the trial
  end (`ensure_practice_open`, `PlanEnded`), HQ block, seats, two-step for admins and every role
  guard apply from the first request.
- **Email path.** The admin is `invited` and gets the existing invite (`send_invite`, a set-password
  link valid 72 hours), so owning the address is proven before anyone signs in.
- **No enumeration.** The route counts the attempt (5 per address and 3 per email per hour),
  validates the form and the time zone, answers 204 and only then, in a background task with its own
  session, looks the email up, as forgot password does. An email that already has an account gets "you
  already have an account: sign in or reset your password" instead of a practice; the response, its
  timing and its body are the same either way.
- **Provider path.** The callback that finds no account sets `bodha_signup`, a signed 30-minute token
  (provider, subject, email, name) in an httpOnly, Secure, SameSite=Lax cookie scoped to `/api/signup`,
  and redirects to `/sign-up/practice`. Nothing is put in the URL. `GET /api/signup/identity` reads
  it; `POST /api/signup/identity` (name, practice, time zone, agreement) creates the practice and an
  `active` admin bound to the subject, clears the cookie and answers what sign-in answers, through
  `services.auth.sign_in_user`: admins get the two-step setup challenge, and the page hands it to the
  sign-in screen as `/sign-in#mfa=…&setup=1`, the same fragment the provider callback already uses.
  The route is `/api/signup/identity` rather than `/api/signup/google` because one cookie serves three
  providers. The name is asked again on that page, prefilled, because Microsoft and Yahoo do not
  always send one.
- **Record of acceptance.** `practices.signup` (JSONB, migration 0008) holds `source` (`self` or `hq`),
  and for self sign-up `agreement_version` (`AGREEMENT_VERSION`), `accepted_at`, `accepted_by` (the
  admin's user id), `method` (`email`, `google`, `microsoft` or `yahoo`) and the address. Practices
  that existed before 0008 and every HQ-created practice carry `{"source": "hq"}`. The HQ activity log
  gets `practice signed up` with the practice name and method.
- **Legal links rule.** `TERMS_URL`, `BAA_URL` and `PRIVACY_URL` are shown as links in the agreement
  checkbox. With no BAA the form says "I will use test data only" (`test_data_only`), because a
  practice must not upload PHI without a business associate agreement. When `APP_ENVIRONMENT` is
  `production` and self sign-up is on, the API refuses to start without `BAA_URL` and `TERMS_URL`
  (`Settings.refuse_unready_signup`, called first in the API lifespan). It is a start-up check rather
  than a settings validator like the demo-model guard because CI, the image smoke test and Alembic
  build `Settings` in the production default without these links and must keep working. A blank link
  counts as unset and anything that is not an `http(s)` address is refused.
- **Off switch.** `SELF_SIGNUP_ENABLED=false` answers 404 "Self sign-up is not available" on the
  sign-up routes, hides the links, and restores the old provider behaviour (`#error=no_account`).
- **Sign-in services as data.** `adapters/oidc_providers.py` is the registry (Google, Microsoft,
  Yahoo): discovery address, scopes `openid email profile`, settings names, signing algorithms,
  required claims, an issuer rule and an email-trust rule. `adapters/oidc.py` is one OpenID Connect
  client for all of them: endpoints from the discovery document (https only), PKCE (S256), state and
  nonce in the signed ten-minute `bodha_oidc` cookie scoped to `/api/auth/{provider}`, signature
  against the provider's published keys, audience, expiry and nonce. A provider is on only when its
  client id and secret are set; `GET /api/auth/providers` lists the ones that are on.
  - Google: issuer `https://accounts.google.com` (or without the scheme), `email_verified` true.
  - Microsoft (multi-tenant, `MICROSOFT_TENANT=common`): the issuer must be
    `https://login.microsoftonline.com/{tid}/v2.0` for the token's own `tid`, and the tenant must be
    allowed by `MICROSOFT_TENANT` (`common`, `organizations`, `consumers` or one tenant id). The email
    is trusted only when `xms_edov` is true (the domain owner verified it; an optional claim the app
    registration must emit) or the account is a personal Microsoft account (tenant
    `9188040d-6c67-4c5b-b112-36a304b66dad`); otherwise the user sees "This Microsoft account has no
    verified email".
  - Yahoo: issuer `https://api.login.yahoo.com`, ES256 or RS256, an email present and
    `email_verified` true whenever Yahoo sends it.
- **One table of identities.** `user_identities` (user, provider, subject; unique per provider and
  subject, and per user and provider) replaces `users.google_sub`; migration 0008 copies the Google
  subjects across and drops the column, and its downgrade copies them back (Microsoft and Yahoo
  bindings are lost on downgrade). The binding rule of 0008 holds per provider: an account bound to
  one subject refuses another subject of the same provider, and a subject bound to one account cannot
  start a sign-up for another email.
- **Brand marks** are inline SVG with their brand colours as tokens. They are logos, not interface
  colour, so the rule that dark purple appears only on the primary button does not apply to Yahoo's
  purple.

## Redirect URIs

Register `{APP_URL}/api/auth/{provider}/callback` with each provider:

| Environment | Google | Microsoft | Yahoo |
|---|---|---|---|
| Local | `http://localhost:3000/api/auth/google/callback` | `http://localhost:3000/api/auth/microsoft/callback` | Yahoo accepts https only: use a TLS tunnel's address |
| Staging | `https://bodha-coder.vercel.app/api/auth/google/callback` | `https://bodha-coder.vercel.app/api/auth/microsoft/callback` | `https://bodha-coder.vercel.app/api/auth/yahoo/callback` |
| Production | `https://www.bodhaai.co/api/auth/google/callback` | `https://www.bodhaai.co/api/auth/microsoft/callback` | `https://www.bodhaai.co/api/auth/yahoo/callback` |

## What HQ still controls

HQ sees every practice with its source and sign-up date, and a "Self sign-up" marker in the table. It
can still create practices, change plan, seats, status and renewal, block, renew, resend the admin
link and delete a practice, and turn self sign-up off for the whole platform.

## Alternatives

- A Google-only sign-up token in the URL fragment would have been simpler but puts an identity token
  in browser history; the cookie keeps it out of reach of scripts and of the address bar.
- A provider-specific route per provider (`/api/signup/google`, `/microsoft`, `/yahoo`) would repeat
  the provider already recorded in the cookie and invite a mismatch between the two.
- Keeping `users.google_sub` beside a new table would leave two sources of truth for Google.

## Follows

- The production task definition needs `BAA_URL` and `TERMS_URL` (or `SELF_SIGNUP_ENABLED=false`)
  before this release reaches it; infra is changed separately.
- `docs/DEPLOY.md` lists the settings and the redirect URIs; `docs/ARCHITECTURE.md` and
  `docs/CORE_API.md` describe the flows and modules.
