from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from gold_cases import GoldCase, GoldSet
from gold_checks import case_categories, pipeline_can_express
from gold_levels import billed_pattern

from app.core.statistics import BOOTSTRAP_RESAMPLES, BOOTSTRAP_SEED
from app.services.agreement import summarize
from app.services.evaluation_scores import evaluation_summary
from app.services.line_agreement import LINE_METRICS

__all__ = ["GROUPS", "CaseResult", "case_results", "group_summaries", "report_markdown"]

PROVISIONAL = (
    "**Provisional.** The expected answers were written by construction under the 2021 and later AMA E/M "
    "guidelines and the 2023 nursing facility rules; no certified coder has checked them yet. Every number "
    "below is provisional until that review is recorded."
)
LINE_LABELS = (
    ("procedures", "Procedure lines exact"),
    ("add_ons", "Add-on codes exact (G2211, G2212, 99417)"),
    ("units", "Units on shared lines"),
    ("place_of_service", "Place of service"),
)
BILLING_LABELS = (
    ("correct", "billed correctly"),
    ("one_high", "one level too high"),
    ("one_low", "one level too low"),
    ("two_high", "two levels too high"),
    ("not_separately_billable", "with a visit code that is not separately billable"),
)
GROUPS: tuple[tuple[str, Callable[[GoldCase], bool]], ...] = (
    ("All gold set cases", lambda case: True),
    ("Cases Bodha's claim can express", pipeline_can_express),
    ("Telehealth", lambda case: bool({"audio_video", "audio_only"} & set(case_categories(case)))),
    *(
        (label, lambda case, tag=tag: tag in case_categories(case))
        for label, tag in (
            ("Office, new patient", "office_new"),
            ("Office, established patient", "office_established"),
            ("Nursing facility, initial", "nursing_initial"),
            ("Nursing facility, subsequent", "nursing_subsequent"),
            ("Level set by MDM", "mdm"),
            ("Level set by time", "time"),
            ("Billed correctly", "correct"),
            ("Billed one level too high", "one_high"),
            ("Billed one level too low", "one_low"),
            ("Billed two levels too high", "two_high"),
            ("Modifier 25 billed or expected", "modifier_25"),
            ("Diagnoses billed differently from expected", "icd_change"),
        )
    ),
)


@dataclass(frozen=True)
class CaseResult:
    case: GoldCase
    result: Mapping[str, Any]

    @property
    def scored(self) -> bool:
        return "agreement" in self.result


def case_results(results: Iterable[Mapping[str, Any]], case_by_note: Mapping[str, GoldCase]) -> list[CaseResult]:
    found = [CaseResult(case_by_note[item["note_id"]], item) for item in results if item["note_id"] in case_by_note]
    return sorted(found, key=lambda item: item.case.id)


def group_summaries(rows: Sequence[CaseResult]) -> list[tuple[str, int, dict[str, Any]]]:
    summaries = []
    for label, wanted in GROUPS:
        chosen = [row for row in rows if wanted(row.case)]
        agreements = [row.result["agreement"] for row in chosen if row.scored]
        if chosen:
            summaries.append((label, len(chosen), summarize(agreements)))
    return summaries


def report_markdown(run: Mapping[str, Any], rows: Sequence[CaseResult], gold: GoldSet) -> str:
    harness = evaluation_summary([row.result for row in rows])
    overall = summarize([row.result["agreement"] for row in rows if row.scored])
    sections = [
        "# Bodha Assure accuracy on the synthetic gold set",
        PROVISIONAL,
        _run_table(run, rows, gold),
        _methods(gold),
        _results_table(harness, overall),
        _groups_table(group_summaries(rows)),
        _disagreements(rows),
        _line_disagreements(rows),
        _failures(rows),
    ]
    return "\n\n".join(section for section in sections if section) + "\n"


def _run_table(run: Mapping[str, Any], rows: Sequence[CaseResult], gold: GoldSet) -> str:
    scored = sum(row.scored for row in rows)
    facts = (
        ("Run", run["id"]),
        ("Status", run["status"]),
        ("Model", run["model"]),
        ("Prompt version", run["prompt_version"]),
        ("Requested", run.get("requested_at") or "n/a"),
        ("Finished", run.get("finished_at") or "n/a"),
        (
            "Gold set cases in the run",
            f"{len(rows)} of {len(gold.cases)}; {scored} scored, {len(rows) - scored} failed",
        ),
    )
    return "## Run\n\n| Item | Value |\n|---|---|\n" + "\n".join(f"| {name} | {value} |" for name, value in facts)


def _methods(gold: GoldSet) -> str:
    patterns = Counter(billed_pattern(case) for case in gold.cases)
    billing = ", ".join(f"{patterns[key]} {label}" for key, label in BILLING_LABELS if patterns[key])
    return "\n".join(
        [
            "## Methods",
            "",
            f"- {len(gold.cases)} synthetic visit notes (office new and established, nursing facility initial and "
            "subsequent, telehealth), each rendered to a clinic-note PDF and uploaded with the claim as billed. "
            f"Visit codes as billed: {billing}. Diagnosis specificity, combination codes, laterality, 7th characters, "
            "missing and unsupported diagnoses and modifier 25 errors are mixed in.",
            "- The expected answer of each case is the correct claim, written by construction with a rationale for "
            "each element (`tools/gold_set/cases.json`), and checked by a validator against the ICD-10-CM release for "
            "the date of service, the CMS fee schedule code list, the NCCI edits and Bodha's Medicare rules.",
            "- An evaluation run reads every case twice with the current model and prompt. The first read is compared "
            "with the expected claim; the two reads are compared with each other for run-to-run consistency.",
            "- Scored elements: the E/M code (exact), the set of ICD-10-CM codes (precision, recall, F1 and exact set) "
            "and the set of modifiers on the claim's CPT and HCPCS lines (exact), on every scored case. Then, each on "
            "the cases it applies to: procedure lines (the set of CPT and HCPCS codes other than the E/M and the "
            "add-ons, when either claim has one), add-on codes (the set of G2211, G2212 and 99417, when either claim "
            "has one), units (the lines both claims carry) and place of service (Bodha does not change it, so it "
            "checks the claim keeps the expected place). Runs before this scoring show these as n/a with 0 trials.",
            "- Intervals: Wilson score 95% intervals for per-note rates; for ICD-10-CM precision and recall a per-note "
            f"percentile bootstrap ({BOOTSTRAP_RESAMPLES} resamples, seed {BOOTSTRAP_SEED}), the note being the unit "
            "of independence. F1 has no interval.",
            "- Bodha's suggested claim can add or replace codes and add modifiers but cannot remove a visit code or a "
            "modifier, so cases that need a removal can only disagree; they are reported with and without those cases.",
        ]
    )


def _results_table(harness: Mapping[str, Any], overall: Mapping[str, Any]) -> str:
    consistency = harness["consistency"]["all"]
    lines = [
        ("E/M exact", _rate(overall["em"])),
        ("Bodha's E/M higher than expected", _rate(overall["em_higher"])),
        ("Bodha's E/M lower than expected", _rate(overall["em_lower"])),
        ("ICD-10-CM precision (codes)", _rate(overall["icd_precision"])),
        ("ICD-10-CM recall (codes)", _rate(overall["icd_recall"])),
        ("ICD-10-CM F1", (_ratio(overall["icd_f1"]), "", "")),
        ("ICD-10-CM exact set", _rate(overall["icd_exact"])),
        ("Modifiers exact", _rate(overall["modifiers"])),
        *((label, _rate(harness[metric])) for metric, label in LINE_LABELS),
        ("Two reads agree on every element", _rate(consistency)),
    ]
    rows = "\n".join(f"| {name} | {value} | {interval} | {count} |" for name, (value, interval, count) in lines)
    return "## Results\n\n| Metric | Agreement | 95% interval | Successes / trials |\n|---|---|---|---|\n" + rows


def _groups_table(summaries: Sequence[tuple[str, int, Mapping[str, Any]]]) -> str:
    header = "| Group | Cases | E/M exact | ICD-10-CM exact set | Modifiers exact |\n|---|---|---|---|---|\n"
    rows = [
        f"| {label} | {count} | {_brief(item['em'])} | {_brief(item['icd_exact'])} | {_brief(item['modifiers'])} |"
        for label, count, item in summaries
    ]
    return "## By group\n\n" + header + "\n".join(rows)


def _disagreements(rows: Sequence[CaseResult]) -> str:
    differing = [row for row in rows if row.scored and not _all_match(row.result["agreement"])]
    if not differing:
        return "## Disagreements\n\nNone."
    header = "| Case | E/M expected | E/M Bodha | ICD missing | ICD extra | Modifiers expected | Modifiers Bodha |\n"
    lines = [_disagreement(row) for row in differing]
    return "## Disagreements\n\n" + header + "|---|---|---|---|---|---|---|\n" + "\n".join(lines)


def _disagreement(row: CaseResult) -> str:
    em, icd, modifiers = (row.result["agreement"][key] for key in ("em", "icd", "modifiers"))
    cells = (
        row.case.id,
        em["reference"] or "none",
        f"{em['compared'] or 'none'} ({em['direction']})",
        ", ".join(icd["missing"]) or "",
        ", ".join(icd["extra"]) or "",
        ", ".join(modifiers["reference"]) or "none",
        ", ".join(modifiers["compared"]) or "none",
    )
    return "| " + " | ".join(cells) + " |"


def _line_disagreements(rows: Sequence[CaseResult]) -> str:
    differing = [row for row in rows if row.scored and _line_misses(row.result.get("lines"))]
    if not differing:
        return ""
    header = "| Case | Procedures expected | Procedures Bodha | Add-ons expected | Add-ons Bodha | Units | Place |\n"
    lines = [_line_disagreement(row.case.id, row.result["lines"]) for row in differing]
    return "## Claim line disagreements\n\n" + header + "|---|---|---|---|---|---|---|\n" + "\n".join(lines)


def _line_disagreement(case_id: str, lines: Mapping[str, Any]) -> str:
    procedures, add_ons, units, place = (lines[metric] for metric in LINE_METRICS)
    differing = [f"{code} {units['reference'][code]} vs {units['compared'][code]}" for code in units["differing"]]
    cells = (
        case_id,
        ", ".join(procedures["reference"]) or "none",
        ", ".join(procedures["compared"]) or "none",
        ", ".join(add_ons["reference"]) or "none",
        ", ".join(add_ons["compared"]) or "none",
        "; ".join(differing),
        "" if place["match"] else f"{place['reference']} vs {place['compared']}",
    )
    return "| " + " | ".join(cells) + " |"


def _line_misses(lines: Mapping[str, Any] | None) -> bool:
    if not lines:
        return False
    return any(lines[metric]["scored"] and not lines[metric]["match"] for metric in LINE_METRICS)


def _failures(rows: Sequence[CaseResult]) -> str:
    failed = [row for row in rows if not row.scored]
    if not failed:
        return ""
    lines = [f"- {row.case.id}: {row.result.get('error') or 'no result'}" for row in failed]
    return "## Cases that did not score\n\n" + "\n".join(lines)


def _all_match(agreement: Mapping[str, Any]) -> bool:
    return all(agreement[key]["match"] for key in ("em", "icd", "modifiers"))


def _rate(rate: Mapping[str, Any]) -> tuple[str, str, str]:
    if rate.get("value") is None:
        return "n/a", "", f"0 / {rate.get('trials', 0)}"
    return (
        _share(rate["value"]),
        f"{_share(rate['low'])} to {_share(rate['high'])}",
        f"{rate['successes']} / {rate['trials']}",
    )


def _brief(rate: Mapping[str, Any]) -> str:
    value, interval, count = _rate(rate)
    return f"{value} ({count}; {interval})" if interval else value


def _share(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.1f}%"


def _ratio(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.2f}"
