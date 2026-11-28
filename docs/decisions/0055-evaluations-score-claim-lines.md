# 0055 Evaluation runs score procedure lines, add-ons, units and place of service

Date: 2026-11-28

Context: an evaluation run scored the visit code, the set of diagnoses and the set of modifiers
([0020](0020-measured-accuracy-and-earned-autonomy.md), [0049](0049-synthetic-gold-set.md)). A claim that
drops a procedure, misses G2212 or bills the wrong units scored as agreeing.

## Choice

`services/line_agreement.py` reads four more elements from a claim (`lines_of(codes, place_of_service)`):

- procedure lines: the set of CPT and HCPCS codes other than the E/M code and the scored add-ons;
- add-on codes: the set of G2211, G2212 and 99417 on the claim (`SCORED_ADD_ONS`);
- units: each non-E/M code's units, summed over its lines (an E/M line is always one unit);
- place of service.

`compare_lines(reference, compared)` gives one note's result, each element with `match` and `scored`:

| Element | Scored on a note when | Agrees when |
|---|---|---|
| Procedure lines | either claim has one | the sets are equal |
| Add-on codes | either claim has one | the sets are equal |
| Units | the claims share at least one non-E/M code | every shared code has the same units |
| Place of service | the reference has one | the places are equal |

A note where neither claim has a procedure tells nothing about procedure coding, so it is not counted;
counting it would fill the rate with easy agreements (about 44 of the 48 gold set cases have no procedure).
Units are compared only on lines both claims carry, so a missing line counts once, under procedures or
add-ons, not again under units.

- The reference is the case's approved claim (`eval_cases.expected.claim`, present on every case) and its
  place of service: `expected.place_of_service`, now recorded when a note is marked; for cases marked
  earlier, the note's place of service, which is the place the approved claim was exported with (a note's
  place of service does not change after upload).
- Bodha's side is the claim of the first read at the default choices, with the place of service of the
  review inputs.
- Each result gains `lines` when its reference has a claim. `evaluation_summary` adds a Wilson rate per
  element (`procedures`, `add_ons`, `units`, `place_of_service`) over the notes it is scored on, and
  `case_counts` with the number of notes behind every element (E/M, ICD-10 and modifiers count every scored
  note; ICD-10 precision and recall count codes, so their trials are not cases).
- Older runs are not recomputed: their stored summaries lack these keys, the API marks every one optional,
  and Insights, Quality, Evaluation shows a dash for them. The gold set report shows them as n/a with 0
  trials and lists each claim line disagreement.
- Drift alerts stay on E/M exact, ICD-10 F1 and modifiers; the new elements apply to few notes and would
  swing by many points on one case.

## Follows

- Bodha never changes the place of service, so its rate measures only that the claim keeps the expected
  place; it moves only if a reference records a different place than the note's (a corrected gold case) or
  if Bodha one day suggests one.
- Run-to-run consistency still covers E/M, ICD-10 and modifiers only.
