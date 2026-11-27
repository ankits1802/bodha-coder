# 0035 Model spend per practice and per provider

Date: 2026-11-28

Context: the owners want to compare what the AI review costs with what each provider pays ($149 or
$249 per provider a month), per practice and per provider, for any period. Every analysis already
stored its model and its input and output tokens (output includes thinking tokens, and the tokens of
top-up calls are summed into the row), and HQ showed a 24-hour token total. No cost was kept.

## Choice

- **Prices are a setting.** `MODEL_PRICES` is a JSON object from model name to `{"input", "output"}` in
  USD per million tokens, parsed into `core.model_prices.ModelPrice` (decimals, never negative, no other
  keys). The default prices the default `GEMINI_MODEL` (`gemini-3.8-flash`) at 0.50 input and 3.00
  output: an estimate, not a quote, to be set from Google's price list for the region and tier in use.
  A table of prices in the database was not chosen: prices change rarely, an operator sets them with
  the other worker settings, and the stored snapshot (below) already keeps history.
- **The cost is kept on the analysis when it is stored, with the prices used.** Migration 0011 adds
  `analyses.cost_microusd` (bigint, null when unknown) and `analyses.price_snapshot` (JSONB,
  `{model: {"input", "output"}}`). `_store_outcome` prices every reply at its own model's price, sums the
  exact amounts and rounds once, half up, to whole microdollars, so a later price change never rewrites
  what a past review cost and no figure is recomputed from today's prices. Microdollars keep a single
  cheap review exact in an integer; money is shown in dollars to the cent.
- **Never guess.** A model missing from `MODEL_PRICES` (matched exactly, as the analysis records it,
  which is Gemini's reported `model_version` when it sends one) leaves the cost and the snapshot null.
  The worker logs the model name once per process through the `PriceBook` it holds in `AnalysisDeps`
  (state held by the caller, not the module); the message carries the model name only. A review with
  no model call (no replies) costs zero.
- **Backfill.** Migration 0011 prices the existing `succeeded` and `superseded` rows whose model is
  `gemini-3.8-flash` at 0.50 and 3.00 with the same arithmetic (`round` in Postgres rounds half away
  from zero, which for these positive amounts is half up), and leaves every other row null. The
  statement is a function of the migration (`backfill_statement`) so a test runs it against rows it
  made.
- **What counts as spend.** Every analysis that consumed tokens, whatever its status: superseded and
  failed runs that recorded tokens were paid for. A run with no tokens (the demo model, a queued run)
  is left out entirely. The range is whole UTC days of `finished_at`, inclusive, and the response says
  `time_zone: "UTC"`; practice calendars were not used because one report spans practices in different
  zones. `analyses.finished_at` gained an index.
- **Grouping.** By the note's practice and its current provider (a note moved to another provider moves
  its spend with it). Each row and the totals carry analyses, distinct notes reviewed, input and output
  tokens, cost to the cent, cost per note to four places (a review costs cents, so a cent would hide the
  difference between providers), and the analyses whose cost is unknown. Unknown costs are counted
  apart, never priced, and make the cost per note `null`, so a total is never silently low; the models
  without a price are listed. Practices carry their plan and its monthly price per provider in cents
  from the plan catalog, for the comparison the owners asked for. No patient name or note text is in
  the response or the CSV.
- **One route, its own modules.** `GET /api/hq/expenditure` (`routes/expenditure.py`,
  `responses/expenditure.py`, `services/expenditure.py`) uses the same HQ guard as the other `/hq`
  routes. The HQ overview reads the same figures for the last 24 hours: `tokens_last_24h` now counts the
  tokens of every analysis that consumed them (any status), and `cost_last_24h_usd` and
  `unpriced_last_24h` sit beside it.
- **The Spend page.** `/hq/spend`, after Practices in the HQ navigation: range presets (this month, last
  month, last 30 days, this year, from the UTC day) as a segmented control that checks nothing for a
  custom range, the range as two compact date pickers (`DateRange` gained a `filter` variant), the range
  in the address, totals in a stat grid, the practices table opening to its providers, and a CSV of the
  provider rows (`bodha-spend-<from>-<to>.csv`, cost to the cent, cost per note to four places).

## Follows

- Keep `MODEL_PRICES` in line with Google's prices, and add an entry for any model name the Spend page
  lists as without a price. Costs already stored are not repriced; a review stored while its model had
  no price stays unknown.
- Evaluation runs (`eval_runs`) also call the model and are not counted here; their tokens are kept on
  the run's results.
- Deleting a practice deletes its analyses, and with them its spend.
