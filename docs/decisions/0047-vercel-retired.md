# 0047 Vercel retired

Date: 2026-11-28

Context: until the domain existed, the public address was `https://bodha-coder.vercel.app` (0025,
amended 2026-11-27) and Vercel later served previews from the operator's machine. Everything now runs on
AWS: the ECS `web` service behind CloudFront at `https://www.bodhaai.co`, with no Vercel deployment.

## Choice

- The subprocessors page drops Vercel Inc. and moves to version 1.2 (same day, so the date stays
  2026-11-28). The AWS hosting row now also names receiving the visit notes practices email to Bodha
  (SES email receiving and Lambda, [0045](0045-email-intake.md)); AWS was already the subprocessor for
  all Customer Data.
- `frontend/vercel.json`, the `VERCEL_PROJECT_PRODUCTION_URL` fallback in `lib/site.ts`, the Vercel
  default of the `public_url` variable (now empty, which means the CloudFront address until
  `domain_live`), the staging Vercel callbacks in DEPLOY.md and the Vercel previews section of the
  infrastructure README are removed.
- `.vercel/` stays in `.gitignore`: the operator's checkout still holds a linked `frontend/.vercel`
  folder with project ids, and the entry keeps it out of commits until it is deleted.

## Follows

- Previews, when wanted, are built and run locally or as a separate ECS service; nothing is hosted
  outside AWS.
