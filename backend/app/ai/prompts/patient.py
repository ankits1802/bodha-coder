from __future__ import annotations

__all__ = ["EXTRACTED_TEXT_TASK", "PATIENT_TASK"]

PATIENT_TASK = """
Return the patient facts exactly as the note states them:
- name: the patient's name as written, or null when the note does not give it
- age: the age in whole years as the note states it; when the note gives only a date of birth, the age on the
  dateOfService; null when neither is stated
- sex: as written (for example "female" or "M"), or null when the note does not state it. Never infer it from a
  name or a diagnosis.
"""

EXTRACTED_TEXT_TASK = """
Transcribe the full readable text of the attached PDF, verbatim and in reading order: every heading, label, line
and value on every page, without summarising, correcting, reordering or leaving anything out. Separate sections and
pages with line breaks. Transcribe text only: do not describe images, and add nothing that is not on the page.
Every other task reviews the note this text records, and its evidence quotes must appear in this text exactly.
"""
