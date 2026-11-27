# 0029 A nonce for every page's scripts

Date: 2026-11-27

Context: `next.config.ts` sent one fixed Content-Security-Policy whose `script-src` allowed
`'unsafe-inline'`, because Next.js writes its bootstrap and page data as inline scripts. Any markup an
attacker managed to inject could therefore run script. Next.js 16 puts a nonce on every script it writes,
but only when the page is rendered for the request that carries the nonce.

## Choice

- `src/proxy.ts` makes a nonce of 16 random bytes (base64) for every page request and sends the policy
  from `lib/contentSecurityPolicy.ts` on the response and on the request. Next.js reads the nonce from the
  request's policy and adds it to its inline scripts and bundle tags. The app writes no script of its own
  (no `next/script`, `<script>` or `dangerouslySetInnerHTML`), so nothing else needs it.
- The production policy, with `<nonce>` new on each request:
  `default-src 'self'; script-src 'self' 'nonce-<nonce>' 'strict-dynamic'; style-src 'self' 'unsafe-inline';
  img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self'; frame-ancestors 'none';
  base-uri 'self'; form-action 'self'; object-src 'none'; upgrade-insecure-requests`.
  `'strict-dynamic'` lets the nonced bootstrap load the route chunks; browsers that honour it ignore
  `'self'`, which stays for older ones. Every other directive is the one `next.config.ts` sent before.
- Development adds `'unsafe-eval'` (React rebuilds server error stacks with eval) and `ws:` and
  `http://localhost:*` for the dev server, and drops `upgrade-insecure-requests`. Only
  `NODE_ENV=development` counts as development, so an unset or unexpected value gets the strict policy.
- Styles keep `'unsafe-inline'`. React writes `style` attributes (progress bars, charts, the landing
  page's motion values) into the server HTML, and a nonce cannot cover an attribute; a nonce in
  `style-src` would also make browsers ignore `'unsafe-inline'` and drop those styles. Injected styles
  cannot run script, and scripts were the goal.
- A nonce that is not base64 is refused with an error, because Next.js silently ignores a malformed one
  and every script on the page would then be blocked.
- `next.config.ts` keeps `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy` and
  `Permissions-Policy` on every path and no longer sends a policy, so no response carries two.
- The proxy skips what is not a page, as the Next.js guide recommends: `/api` (the backend rewrite, whose
  large uploads must not be buffered by a proxy, [0016](0016-containers-and-deployment.md)),
  `/_next/static`, `/_next/image`, `/icon.svg`, `/opengraph-image`, `/robots.txt`, `/sitemap.xml`,
  `/manifest.webmanifest` and router prefetches. A missing file such as `/favicon.ico` still passes
  through it, because its not-found page is HTML.

## Dynamic rendering

A page built ahead of time has no request and so no nonce, and the policy would block its scripts. The
root layout therefore awaits `connection()`, and every page renders per request: the landing, pricing
and legal pages are no longer prerendered (the legal page keeps `generateStaticParams` as its list of
documents). What stays static and cached: `/_next/static` (immutable, cached by CloudFront), and the
icon, share image, robots, sitemap and manifest, which sit outside the layout. CloudFront already cached
nothing but `/_next/static` (`infra/tofu/modules/app/edge.tf`), so the edge loses nothing; the cost is
server rendering on each page view. Hash-based subresource integrity would keep pages static, but it is
experimental in Next.js 16.

`global-error.tsx` is a client component and cannot wait for the request, so Next.js still builds it
ahead of time. If the server ever falls back to that copy, the page shows but its scripts, and with them
its retry button, are blocked.

## Follows

- A script added later must carry the nonce: the proxy then also passes it in an `x-nonce` request
  header and a server component reads it with `headers()` and gives it to `next/script`. With
  `'strict-dynamic'` a host list in `script-src` is ignored, so a third-party script is trusted only
  through that nonce; the hosts it calls join `connect-src` or `img-src`.
- The landing page's response time before and after this change has not been measured; compare it on
  staging after the next deploy.
- Tests: `lib/__tests__/contentSecurityPolicy.test.ts` (the policy and the nonce),
  `__tests__/proxy.test.ts` (headers, matcher, and that `next.config.ts` sends no policy) and
  `__tests__/rootLayout.test.ts` (the layout waits for the request).
