# 0027 Our own select and date picker

Date: 2026-11-27

Context: native selects and date inputs drew each browser's own menu and calendar, so the same field
looked different on every platform, the calendar ignored the app's day format and week, and a long list
such as places of service could not be searched. The owner asked for branded, accessible replacements,
preferably without a new dependency.

## Choice

- `components/ui/Select` replaces every native select. Options are data (`value`, `label`, `disabled`,
  `tone`, `group`) and `onChange` receives the value rather than an event, so types such as roles and plan
  types flow through without casts. `FilterSelect` is gone; filter bars use `variant="filter"`.
- It follows the WAI-ARIA select-only combobox: a button with role `combobox` that keeps focus and points
  at the highlighted option with `aria-activedescendant`. Lists of more than twelve options open with a
  search box, itself a combobox over the same listbox. Twelve keeps the month list in the calendar plain.
- Panels are positioned `fixed` inside their own subtree instead of a portal to `body`: a modal `<dialog>`
  makes everything outside it inert, so a portalled list would be unreachable from dialogs, while fixed
  positioning escapes the overflow clipping of dialogs and tables. `useFloating` holds this for `Select`,
  `DatePicker` and `MenuButton`.
- `components/ui/DatePicker` shows and reads days in the app's en-GB format, starts weeks on Monday
  (`WEEK_STARTS_ON`), and exchanges ISO days or `null`, so no screen changed its data handling. Text that
  cannot be read or lies outside `min` and `max` is flagged when the field loses focus and never passed on.
  The calendar is the WAI-ARIA date picker dialog: modal, focus kept inside, grid keys by day, week, month
  and year. `DateRange` limits each end by the other.
- No dependency was added.

## Follows

- `features/sign-up/DraftFields.tsx` moved to `components/ui/Select` and the native `Select` export left
  `components/ui/Input`; no native `<select>` remains in the app.
