# 0065 Appearance: theme, text size and reduce motion for each person

Date: 2026-11-28

Context: the app had one light theme, fixed text sizes and motion that followed only the system's
reduced-motion setting. Practice users and HQ asked to choose a dark theme, larger text and less (or
not less) motion, and to have the choice follow them from one computer to another.

## Choice

- **Three settings, one panel.** Theme (System, Light, Dark), Text size (Default, Large, Larger) and
  Reduce motion (System, On, Off), as segmented controls in an Appearance panel on Account (practice) and
  Security (HQ). System is the default for all three.
- **Stored on the person.** Three columns on `users` (`theme`, `text_size`, `reduce_motion`, migration
  0028, checked by the database), like the daily summary's `notify_digest`. `GET` and `PUT
  /api/auth/appearance` take any session, HQ and billing-only included, because the choice belongs to the
  person, not to a practice. Unlike the daily summary, a change writes no activity row: a display
  preference changes nothing anyone else sees and nothing about PHI, and the hash-chained activity log is
  for administrative changes. `PUT` replaces all three values.
- **Mirrored on the device.** The browser keeps `bodha_appearance=theme.text_size.reduce_motion` (path `/`,
  400 days, `SameSite=Lax`, `Secure` over HTTPS; not HttpOnly, since the page writes it). It is not a
  secret and holds nothing about the person. A missing or unknown part reads as System, which is what a
  device that kept nothing shows.
- **No flash.** The root layout already renders per request (`connection()`, for the CSP nonce), so it
  reads the cookie and renders `<html>` with `data-theme`, `data-text-size` and `data-motion` (none for
  System). No inline script is needed and the CSP is unchanged. Public pages and sign-in therefore show
  System plus whatever the device keeps; the cookie stays after sign-out.
- **Following the person.** `AppearanceSync`, in the practice and HQ layouts, reads the saved appearance
  once a person is signed in and applies it, which also rewrites the cookie: on a new device the first
  page shows the device's appearance and the person's own follows as soon as the session is known. If the
  read fails, the device's appearance stays.
- **Live.** A choice sets the attributes and the cookie at once and is saved in the background, one
  request at a time with the latest choice, so a quick run of choices cannot land out of order. A failed
  save keeps the choice on the device and shows the error.
- **Dark palette.** The light values stay in `@theme static` (static, so tokens used only by CSS modules
  are always emitted); `@variant dark` on `:root` overrides the themed colours. The `dark` variant is
  `data-theme="dark"`, or the system's dark scheme unless `data-theme="light"`, defined once. Shadows are
  built from colour tokens with `color-mix`: rings from `--color-shade` (black, white in dark), drop
  shadows from `--color-shadow` (always black), because Tailwind writes a shadow's value into the
  utility and an overridden `--shadow-*` would never reach it. Every text pair was measured: the lowest
  is 5.1:1 (secondary text on the lightest fill, the bad tone on row fills). The purple is lighter in dark,
  #7357CC, giving white text 5.3:1 and the button 3.2:1 against the surface; it is still the only purple.
- **What does not change with the theme.** White on purple and on status fills, toggle knobs, paper and
  ink for signatures and the two-step QR code (a signature drawn in dark mode is still stored dark on white
  and stamped as such), the landing's dark band and the phone in its pictures. `--color-dark` is replaced
  by `inverse` and `on-inverse`, which flip.
- **Text size by tokens, not the root font size.** Every text token is `calc(size * var(--text-scale))`.
  Scaling the root font size would also scale every spacing, height and width in rem while media queries
  keep measuring in the browser's own rem, so a Larger desktop would get the desktop layout with less room
  than a smaller window; scaling text alone keeps the layout and lets rows wrap and tables scroll as they
  already do. Display sizes scale by half as much, so large titles fit a phone. The landing's CSS modules
  scale their reading text; its product pictures keep their drawn sizes, as images of text.
- **Motion from one attribute and the system.** `motion-reduce` and `motion-safe` are redefined once in
  `globals.css`: reduced when `data-motion="reduce"`, or when the system asks for less and
  `data-motion` is not `"full"`. The landing's CSS modules use the same variants through `@reference`
  instead of their own media queries. Reduced motion also ends every transition and animation at once,
  app-wide (the spinner stops too: busy state is also shown by `aria-busy` and the disabled look).
  `prefersReducedMotion()` reads the same attribute first, so the landing's scripts agree with its CSS.
  Off lets the system setting be ignored; the app adds no motion of its own for it.
- **Checked in CI.** The sweep runs every file three times: `sweep`, `sweep-dark` (the browser's dark
  scheme, so the System path) and `sweep-larger` (Larger on the device, with the person's saved appearance
  answered with the same so the sync does not undo it). A few screens also run with Reduce motion On (no
  loop may run although the system asks for nothing) and the landing with Off (its loops run although the
  system asks for less). A journey chooses Dark, Larger and On, clears the cookie, reloads, and finds the
  saved choice back; the next page's HTML already carries the attributes.

## Alternatives

- **A preferences table with one row per change**: the history of a display preference has no use, and the
  current value is what every read needs.
- **`localStorage` and an inline script with the nonce**: works, but the layout already renders per
  request, and a cookie lets the server render the right attributes with no script at all.
- **Applying the device's value over the saved one**: the device would win on a shared computer, and a
  change made elsewhere would never arrive.
- **Duplicating each landing reduced-motion block under the attribute**: two copies of every rule that
  drift; the variant keeps one.

## Follows

- `docs/DESIGN.md` (Type, Colour, Appearance, Motion, Landing page), `docs/ARCHITECTURE.md` (Data model,
  Web client data, Browser journeys), `docs/CORE_API.md` (`lib/appearance.ts`, `lib/media.ts`,
  `AppearanceSync`, the variants) and `README.md` (Checks).
- There is no PDF viewer in the app (notes open as text and PDFs download), so nothing renders a PDF on a
  dark surface.
