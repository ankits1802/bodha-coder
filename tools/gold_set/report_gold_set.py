from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from gold_api import DEFAULT_BASE_URL, ApiError, BodhaApi, Credentials, SetupError
from gold_cases import GoldCase, GoldSet, load_gold_set
from gold_loading import check_practice, find_note
from gold_report import case_results, report_markdown
from render_notes import OUT_DIR

REPORT_DIR = OUT_DIR.parent / "reports"
FINISHED = "done"


def chosen_run(runs: Sequence[Mapping[str, Any]], run_id: str | None) -> Mapping[str, Any]:
    for run in runs:
        if (run_id is None and run["status"] == FINISHED) or run["id"] == run_id:
            return run
    raise SetupError(f"no evaluation run {run_id}" if run_id else "the practice has no finished evaluation run")


def notes_of_cases(api: BodhaApi, gold: GoldSet) -> dict[str, GoldCase]:
    found = {}
    for case in gold.cases:
        note = find_note(api, case)
        if note is not None:
            found[note["id"]] = case
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description="Write the methods and results of the latest gold set evaluation.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--run-id", help="a specific evaluation run; the latest finished one by default")
    parser.add_argument("--output", type=Path, help="the Markdown file to write")
    args = parser.parse_args()
    gold = load_gold_set()
    try:
        output = _report(args, gold)
    except (SetupError, ApiError) as error:
        sys.stdout.write(f"no report: {error}\n")
        return 2
    sys.stdout.write(f"wrote {output}\n")
    return 0


def _report(args: argparse.Namespace, gold: GoldSet) -> Path:
    credentials = Credentials.from_environment(os.environ)
    api = BodhaApi.open(args.base_url)
    try:
        api.sign_in(credentials)
        check_practice(api, credentials)
        run = chosen_run(api.get("/api/quality/evaluations")["runs"], args.run_id)
        detail = api.get(f"/api/quality/evaluations/{run['id']}")
        rows = case_results(detail["results"], notes_of_cases(api, gold))
    finally:
        api.close()
    output = args.output or REPORT_DIR / f"evaluation-{run['id']}.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report_markdown(detail["run"], rows, gold), encoding="utf-8", newline="\n")
    return output


if __name__ == "__main__":
    raise SystemExit(main())
