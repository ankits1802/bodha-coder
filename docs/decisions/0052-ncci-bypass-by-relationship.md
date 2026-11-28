# 0052 NCCI pair edits are bypassed by the modifier that fits the pair

Date: 2026-11-28

Context: the claim check treated an anatomic modifier on one line as bypassing a procedure-to-procedure
(PTP) edit whenever the other line lacked that modifier ([0019](0019-ncci-edits-and-payer-rules.md)). So
20610-RT with a same-day 99214 that had no modifier 25 showed "Bypassed with RT", and 69210-LT with 99214
likewise (gold set case GS-24, [0049](0049-synthetic-gold-set.md)). RT and LT say which side a procedure
was on; they do not make a visit separately identifiable from the procedure. The same reading let 59, XS
or the other procedure modifiers on the procedure line bypass an E/M edit.

## Sources

2026 Medicare NCCI Policy Manual, chapter I (General Correct Coding Policies), revision 1/1/2026, the
manual named in `ncci_practitioner.meta.json`:

- Section D, Evaluation & Management (E&M) Services (page I-13): a procedure with a global period of 000 or
  010 days is a minor surgical procedure; E&M services on its date are included in its payment, and "a
  significant and separately identifiable E&M service unrelated to the decision to perform the minor
  surgical procedure is separately reportable with modifier 25". The same section gives 57 for the decision
  for a major procedure and 24 for an unrelated visit in a postoperative period. 20610 has a 000 global
  period.
- Section E, Modifiers and Modifier Indicators (pages I-14 and I-15): the PTP-associated modifiers are the
  anatomic E1-E4, FA, F1-F9, TA, T1-T9, LT, RT, LC, LD, RC, LM and RI, the global surgery 24, 25, 57, 58,
  78 and 79, and 27, 59, 91, XE, XS, XP and XU; their use relates "to separate patient encounters, separate
  anatomic sites, or separate specimens", and edits on paired organs carry indicator 1 "because the 2 codes
  of the code pair edit may be reported if performed on the contralateral organs or structures".
- Section E, item b, Modifier 25 (pages I-15 and I-16): 25 is appended to the E&M code reported with a
  minor surgical procedure or an XXX procedure.
- Section E, item d, Modifier 59 (page I-17): "Modifier 59 should not be appended to an E/M service. To
  report a separate and distinct E/M service with a non-E/M service performed on the same date, see
  modifier 25"; and a PTP pair of procedures "may be reported together when the 2 procedures are performed
  at 2 different patient encounters or 2 different anatomic sites".
- Section E, item a (page I-15): "both services may be reported with the NCCI PTP-associated modifier",
  the basis in 0019 for accepting a procedure modifier on either line of a procedure pair, kept here.

## Choice

`codes/ncci.py` decides the bypass of an indicator 1 edit by the kind of pair:

- A pair with an E/M code (an E/M and a procedure, or two E/M codes): only 24, 25 or 57 on the E/M line.
  59, X{EPSU}, 58, 78, 79, 91, 27 and anatomic modifiers on either line do not bypass it.
- A pair of procedures: 27, 58, 59, 78, 79, 91, XE, XP, XS or XU on either line; or an anatomic modifier
  when both lines carry one and they share none, so the claim itself shows two sites (20611-RT with
  20610-LT bypasses; 20611-RT with 20610-RT, or with a bare 20610, does not).

Indicator 0 is still never bypassed. Rejected: accepting an anatomic modifier on one line alone. CMS claim
systems pay an edit when a PTP-associated modifier is on either code, but the manual allows anatomic
modifiers only for different sites, and one RT does not show a second site; Bodha reports the edit and the
coder can add the second site or XS when the note documents it.

## Follows

- 20610-RT or -LT with a same-day E/M without 25 now shows "Cannot be billed together" with "Modifier
  allowed"; with 25 on the E/M it shows "Bypassed with 25".
- Not distinguished: two anatomic modifiers that name the same side in different ways (RT with T5, a right
  toe) count as different sites.
- The gold set validator now takes the bypass from `claim_edits` instead of re-checking E/M pairs itself.
- Amends the PTP-associated modifier paragraph of [0019](0019-ncci-edits-and-payer-rules.md).
