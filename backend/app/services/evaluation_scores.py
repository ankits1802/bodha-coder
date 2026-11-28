from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from app.core.statistics import wilson
from app.services.agreement import summarize
from app.services.line_agreement import LINE_METRICS, summarize_lines

__all__ = ["DROP_ALERT", "TRACKED_METRICS", "evaluation_summary", "metric_values", "run_change"]

DROP_ALERT = 0.05
DELTA_DIGITS = 9
TRACKED_METRICS = ("em", "icd_f1", "modifiers")
ELEMENTS = ("em", "icd", "modifiers")


def evaluation_summary(results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    scored = [result for result in results if "agreement" in result]
    measured = summarize([result["agreement"] for result in scored])
    lines = summarize_lines([result["lines"] for result in scored if "lines" in result])
    repeats = [result["repeat"] for result in scored]
    return {
        "cases": len(results),
        "scored": len(scored),
        "failed": len(results) - len(scored),
        **{key: measured[key] for key in ("em", "em_higher", "em_lower", "icd_precision", "icd_recall", "icd_f1")},
        "modifiers": measured["modifiers"],
        **lines,
        "case_counts": {
            **{element: len(scored) for element in ELEMENTS},
            **{metric: lines[metric]["trials"] for metric in LINE_METRICS},
        },
        "consistency": {
            **{
                element: wilson(sum(repeat[element]["match"] for repeat in repeats), len(repeats)).as_json()
                for element in ELEMENTS
            },
            "all": wilson(sum(_repeated_exactly(repeat) for repeat in repeats), len(repeats)).as_json(),
        },
    }


def metric_values(summary: Mapping[str, Any]) -> dict[str, float | None]:
    return {
        "em": (summary.get("em") or {}).get("value"),
        "icd_f1": summary.get("icd_f1"),
        "modifiers": (summary.get("modifiers") or {}).get("value"),
    }


def run_change(previous: Mapping[str, Any] | None, current: Mapping[str, Any]) -> dict[str, Any] | None:
    if previous is None:
        return None
    before, after = metric_values(previous), metric_values(current)
    deltas = {
        metric: round(after[metric] - before[metric], DELTA_DIGITS)
        for metric in TRACKED_METRICS
        if after[metric] is not None and before[metric] is not None
    }
    dropped = [metric for metric, delta in deltas.items() if -delta > DROP_ALERT]
    return {"deltas": deltas, "dropped": dropped, "status": "dropped" if dropped else "holding"}


def _repeated_exactly(repeat: Mapping[str, Any]) -> bool:
    return all(repeat[element]["match"] for element in ELEMENTS)
