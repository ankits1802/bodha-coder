from __future__ import annotations

import argparse
import sys
from pathlib import Path

from gold_cases import GoldCase, GoldSet, load_gold_set
from gold_checks import check_gold_set, load_code_sets
from gold_pdf import render_note

OUT_DIR = Path(__file__).resolve().with_name("out") / "pdf"


def chosen_cases(gold: GoldSet, wanted: str | None) -> list[GoldCase]:
    if not wanted:
        return list(gold.cases)
    return [gold.case(case_id.strip()) for case_id in wanted.split(",") if case_id.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Render the gold set visit notes to PDF.")
    parser.add_argument("--out", type=Path, default=OUT_DIR)
    parser.add_argument("--cases", help="comma-separated case ids, for example GS-01,GS-27")
    args = parser.parse_args()
    gold = load_gold_set()
    problems = check_gold_set(gold, load_code_sets())
    if problems:
        sys.stderr.write("the gold set is not valid:\n" + "\n".join(problems) + "\n")
        return 1
    args.out.mkdir(parents=True, exist_ok=True)
    cases = chosen_cases(gold, args.cases)
    for case in cases:
        (args.out / case.file_name).write_bytes(render_note(case, gold))
    sys.stdout.write(f"wrote {len(cases)} PDFs to {args.out}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
