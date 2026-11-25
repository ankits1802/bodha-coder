from __future__ import annotations

__all__ = ["SUGGESTED_TEXT_RULES", "TARGETING_INSTRUCTION"]

TARGETING_INSTRUCTION = """
REFINING A DIAGNOSIS CODE (optional, and omitted by default)

When an item REFINES the code of a diagnosis rather than adding a condition, name the refinement:
  "replacesIcdCode":    the ICD-10-CM code the condition carries today: the billed code from the ENCOUNTER
                        CONTEXT when the claim bills one for it, otherwise the code the note's current wording
                        supports
  "suggestedIcdCode":   the more specific ICD-10-CM code the item's recommendation would support
  "suggestedDiagnosis": the diagnosis NAME that belongs beside that code, COMPLETE: never a template with
                        [brackets] in it

suggestedIcdCode and suggestedDiagnosis GO TOGETHER: emit both or neither. replacesIcdCode may be omitted when you
are not certain which code the condition carries today.

OMIT THE WHOLE GROUP when:
  - the code you would suggest is the one the condition already carries;
  - you would have to leave a [placeholder] in the diagnosis name.

A wrong code is a wrong billed diagnosis. An omitted refinement costs nothing.
"""

SUGGESTED_TEXT_RULES = """
targetSection and suggestedText are wording the provider may choose to add to the record in an addendum. They are
written for the CHART, and suggestedText is shown to the provider exactly as you write it. Therefore:
- targetSection names ONE section of the note as a lowercase key: "subjective", "objective", "assessment" or
  "plan". Prefer "assessment" for diagnostic specificity, "plan" for an action, order, follow-up or counselling
  item, and "subjective" or "objective" for history or examination detail.
- Write PLAIN TEXT ONLY: no markdown, no "#", no "**", no leading "-", "*" or bullet characters, no code fences, no
  numbering.
- Write complete sentences in the clinician's voice, as they would appear in the note ("Chronic kidney disease
  stage 3b, eGFR 38 mL/min."), NOT instructions about the note, and NEVER a question.
- Never emit a [PLACEHOLDER: ...] token, and never invent a clinical finding, value or measurement the note does
  not already support. If the wording would need information the note does not contain, leave suggestedText
  EMPTY: an empty one costs nothing, while an invented one would put into a patient's record a fact nobody
  observed.
- Keep it under 400 characters.
"""
