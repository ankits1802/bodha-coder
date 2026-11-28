# 0063 People stay signed in for days, not minutes

Date: 2026-11-28

Context: the owner found being signed out every 15 minutes a constant hassle, for practice users and
for HQ alike, and asked for sign-in to last as long as possible. Four limits produced the sign-outs: the
browser's inactivity timer (practice choice of 5, 10, 15 or 30 minutes, 15 by default; HQ fixed at 15), the
server refusing to refresh a session unused for 30 minutes, and refresh sessions ending after 7 days.

## Choice

- The browser signs out after 7 days without use by default, for every practice role and for HQ.
  Practice admins can still choose a shorter time in Settings, Security: 15 or 30 minutes, 1, 4 or 8 hours,
  1 day or 7 days (`practice_setup.IDLE_MINUTES_CHOICES`). Migration 0027 moves every practice to 7 days,
  because 5 and 10 minutes are no longer offered.
- The server keeps a session refreshable for 7 days without use (`SESSION_IDLE_MINUTES = 10080`) and for
  30 days in all (`REFRESH_TOKEN_DAYS = 30`); the refresh cookie lasts as long. The 15-minute access token
  is unchanged: the browser renews it silently while the session lives, so it never signs anyone out.
- Ending sessions still works as before: signing out, removing a device, a password change, two-step
  changes, a block or removal, and an admin's "sign out everywhere" end sessions at once.
- Two-step verification is still asked at each new sign-in for HQ and the roles a practice chooses.
