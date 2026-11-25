# 0008 Google sign-in, recovery codes and account security

Context: the owner asked for password reset, Sign in with Google, recovery codes for two-step
verification, rate limits that hold across API processes, a list of signed-in devices, and, from the
legacy review, admin-sent password resets, an ended-plan check, TOTP replay protection and encrypted
TOTP secrets.

Choice:

- **Google runs server-side**: OpenID Connect authorization code flow with PKCE (S256), the code
  exchanged and the ID token verified by the API (`adapters/google_oidc.py`, RS256 against Google's
  published keys, audience, issuer, expiry, nonce and a verified email). The browser never holds a
  Google token, so a script on the page cannot replay one, and the client secret stays on the
  server. State, nonce and verifier live in a signed ten-minute cookie scoped to
  `/api/auth/google`; it is SameSite=Lax because Google's redirect back is a cross-site navigation.
- **The Google subject is bound** to the account on first use (`users.google_sub`) and required
  afterwards, so an email address later moved to a different Google account cannot take over a
  Bodha account.
- **No self sign-up**: Google signs in only an existing account with the same email. An invited
  member whose email Google verified becomes active. Practices still control who joins.
- **Two-step still applies**: password and Google sign-in share one policy
  (`services.auth.sign_in_user`), so roles that need two-step verification get the code step after
  Google too.
- **Recovery codes**: ten single-use codes of sixteen characters from a 31-letter alphabet (about 79
  bits each), so an unsalted SHA-256 hash is safe to store; they are shown once when two-step setup
  completes and replaced only after a current six-digit code.
- **Rate limits in Postgres** (`rate_events`, keys hashed, a per-key advisory lock): login 10 per email
  and 30 per address per 15 minutes; forgot password 3 per email and 10 per address per hour; two-step
  codes 10 per user per 15 minutes; Google returns 30 per address per 15 minutes; provider codes 5 per
  request per hour; demo requests 5 per address per hour.
- **Forgot password answers before it looks**: the response is a 204 sent before the account lookup,
  which runs as a background task, so timing says nothing about whether the account exists.
- **Signing out a device bumps the token version**: every access token stops at once; devices that
  still hold a live refresh session renew silently.
- **TOTP**: the last accepted step is stored and a code must be for a newer step. Secrets are
  encrypted with Fernet under `MFA_ENCRYPTION_KEY` and stored as `v1:<token>`; unprefixed legacy
  secrets are accepted and re-saved encrypted after their first good code. Migration 0003 decrypts
  them again on downgrade, which needs the same key.
- **Plan end**: a practice whose `renews_on` is before today in its time zone is refused with 403 at
  sign-in and on every request, checked in `core.deps.ensure_practice_open`.

Follows: register `{APP_URL}/api/auth/google/callback` with Google. Losing `MFA_ENCRYPTION_KEY`
means every user sets up two-step again. Per-address limits need uvicorn to trust the web server's
forwarded address. HQ users get recovery codes at setup but have no screen to see their devices or
replace codes yet.
