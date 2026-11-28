# 0056 HQ sets the plan with the renewal, and a practice's status follows its plan

Date: 2026-11-28

Context: HQ could change a practice's plan only from the Edit dialog of the practice list. The practice
page and the organization page offered Renew, which set only the end date. Changing the plan from Edit
also left `practices.status` as it was. A trial practice moved to Enterprise kept `status = 'trial'`,
so its admins still saw the trial banner ("trial days left") and the plan screen said Trial, because
the standing and the days left read `status`, not `plan`. Sign-up, combined billing and subscriptions
already set the status from the plan; only the two HQ paths didn't.

## Choice

- `POST /api/hq/practices/{id}/renew` and `POST /api/hq/organizations/{id}/renew` take an optional
  `plan` with `until`, change both in one transaction and answer `{renews_on, plan}`. The activity entry
  names the plan and the end date and lists the plan change beside the renewal date. The renewal dialog
  (practice page, practice list, organization page) has a Plan dropdown that starts on the current plan.
- `services.hq.status_for_plan(status, plan)`: a practice whose status is `trial` or `active` becomes
  `trial` on the trial plan and `active` on any other. Ended, blocked, closed and purged keep their status.
  HQ's Edit and the renewal both apply it; an explicit status chosen in Edit still wins.
- Migration 0023 repairs the rows already out of step: `status = 'active'` where the status is `trial`
  and the plan is not. It has no downgrade, because the earlier state was the defect.
- `lib/format.sentenceCase(text)` capitalises the first letter and writes the word "hq" as "HQ" (not
  inside an email address, a path or another word). Server messages, HQ activity action names, setup field
  names and comment roles use it, so the app never shows "Hq". Stored activity rows keep their text; only
  the display changes, because those rows are append-only and hash-chained.
