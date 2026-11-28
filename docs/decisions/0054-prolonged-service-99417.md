# 0054 CPT 99417 for prolonged office time, beside Medicare's G2212

Date: 2026-11-28

Context: Bodha's code list is the CMS physician fee schedule list, where 99417 has status I (not valid for
Medicare). A commercial claim carrying 99417 therefore got a "Not in the CMS fee schedule" review item that
blocks approval, although commercial payers pay it; Medicare pays prolonged office time as G2212, which the
list has ([0049](0049-synthetic-gold-set.md)). The prompt already described both codes but nothing checked
them.

## Rules

One module, `codes/prolonged.py`, holds them for both codes:

| | 99417 (CPT, commercial and other payers) | G2212 (Medicare) |
|---|---|---|
| Visit codes | 99205, 99215 | 99205, 99215 |
| First unit | 75 minutes with 99205, 55 with 99215 | 89 minutes with 99205, 69 with 99215 |
| Further units | one per further full 15 minutes | one per further full 15 minutes |
| Level selection | by documented total time only | by documented total time only |

The 99417 descriptor reads "beyond the required time of the primary service when the primary service level
has been selected using total time, each 15 minutes of total time"; 99205 requires 60 minutes and 99215 40
(CPT office or other outpatient E/M guidelines, 2024 and later), so the first unit is at 75 and 55 minutes.
Medicare's G2212 starts 15 minutes after the top of the former ranges, 74 and 54 minutes (CMS MLN006764,
Evaluation and Management Services, May 2026, the edition `catalog_pfs.py` names; `MLN_PAGES` places G2212
on pages 5 and 15 to 17). A partial period is not a unit. These are the thresholds the prompt already gave.

## Where each rule applies

- Code list: `billing_codes.KNOWN_CPT_CODES` is the fee schedule list plus `prolonged.OUTSIDE_FEE_SCHEDULE`
  (99417), so a billed 99417 no longer blocks approval. The vendored fee schedule module stays as CMS
  publishes it. `fees.py` still prices 99417 at nothing (no Medicare rate), so estimates list it as unpriced.
- Suggestions (`services/code_additions.py`): an add-on 99417 or G2212 the model names is a suggestion only
  when the visit code Bodha supports is 99205 or 99215, the E/M answer's basis is `Time` with a total time,
  the time reaches the first unit, and the units are what the time gives; otherwise it is shown as "Add-on
  code not confirmed" with the reason and is never added.
- Billed lines (`services/findings.py`): a billed 99417 or G2212 is checked against the same E/M answer. No
  unit due (another visit code, a level by MDM or no time, time short of the first unit): a `remove`
  suggestion. Units due but different: a `replace` suggestion to the same code with the units due
  (`detail.units`), which `routing.claim` now applies. Both default to accept and take a reason to keep, like
  the model's own code review verdicts. Without an E/M answer the line is left to the code review.
- Payer rules (`codes/payer_rules.py`): `prolonged_medicare`, 99417 on a Medicare claim (denial; Medicare
  wants G2212) or a Medicare Advantage claim (risk; plans set their own policy, many follow CMS). New
  `prolonged_without_visit` (denial, any payer, with or without a payer on the note, like
  `initial_visit_repeated`): 99417 or G2212 on a claim without 99205 or 99215. The NCCI add-on table still
  applies its own wider primary list.
- Prompt (`ai/prompts/em.py`, `PROMPT_VERSION` 2026.11.7): 99417 only with 99205 or 99215 at basis `Time`,
  never with a level resting on MDM, and the level is set by time when the documented total time reaches the
  prolonged threshold, even if MDM gives the same code, so the add-on can be reported.
- Claim lines, the claim line CSV and JSON carry 99417 like any line, with its units and, by the NCCI add-on
  table, its primary's diagnosis pointers. There is no 837P mapping in Bodha to change.

## Choices

- The payer is not known when the note is read (it is set later), so the model cannot choose between 99417
  and G2212 for certain; the claim check catches the wrong one once the payer is set.
- Only 99205 and 99215, as asked. CPT 2023 and later, and the NCCI add-on table, also list 99245, 99345,
  99350 and 99483 (and the 2025 telemedicine codes) as primaries of 99417; Bodha refuses those pairs until a
  certified coder confirms which to allow.
- G2212 now goes through the same checks; before, any suggested G2212 was accepted as the model gave it.

## Follows

- The gold set validator computes the prolonged units it expects from `prolonged.py` for both codes (G2212
  for Medicare cases, 99417 for the others) instead of its own copy of the Medicare thresholds.
