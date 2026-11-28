from __future__ import annotations

import argparse
import os
import sys
import time
from collections import Counter
from collections.abc import Callable

from gold_api import (
    DEFAULT_BASE_URL,
    ENV_EMAIL,
    ENV_PASSWORD,
    ENV_PRACTICE,
    ENV_TOTP,
    ApiError,
    BodhaApi,
    Credentials,
    SetupError,
)
from gold_cases import GoldCase, GoldSet, load_gold_set
from gold_checks import case_categories, check_gold_set, load_code_sets
from gold_loading import LoadContext, Waiting, all_loaded, load_cases, preflight, summary_lines
from gold_pdf import render_note
from render_notes import chosen_cases

POLL_SECONDS = 15.0
TIMEOUT_MINUTES = 30.0


def dry_run_lines(gold: GoldSet, cases: list[GoldCase], render: Callable[[GoldCase], bytes]) -> list[str]:
    sizes = [len(render(case)) for case in cases]
    tags = Counter(tag for case in cases for tag in case_categories(case))
    lines = [f"{len(cases)} cases valid; {len(sizes)} PDFs rendered ({sum(sizes)} bytes)"]
    lines += [f"  {tag}: {count}" for tag, count in sorted(tags.items())]
    lines += [
        f"{name}: {'set' if os.environ.get(name) else 'not set'}"
        for name in (ENV_EMAIL, ENV_PASSWORD, ENV_TOTP, ENV_PRACTICE)
    ]
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description="Load the synthetic gold set into the evaluation practice.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--dry-run", action="store_true", help="validate the data and render the PDFs; call nothing")
    parser.add_argument("--cases", help="comma-separated case ids, for example GS-01,GS-27")
    parser.add_argument("--poll-seconds", type=float, default=POLL_SECONDS)
    parser.add_argument("--timeout-minutes", type=float, default=TIMEOUT_MINUTES)
    args = parser.parse_args()
    gold = load_gold_set()
    problems = check_gold_set(gold, load_code_sets())
    if problems:
        _write("the gold set is not valid:", *problems)
        return 1
    cases = chosen_cases(gold, args.cases)

    def render(case: GoldCase) -> bytes:
        return render_note(case, gold)

    if args.dry_run:
        _write(*dry_run_lines(gold, cases, render))
        return 0
    try:
        return _load(args, gold, cases, render)
    except (SetupError, ApiError) as error:
        _write(f"not loaded: {error}")
        return 2


def _load(args: argparse.Namespace, gold: GoldSet, cases: list[GoldCase], render: Callable[[GoldCase], bytes]) -> int:
    credentials = Credentials.from_environment(os.environ)
    api = BodhaApi.open(args.base_url)
    try:
        api.sign_in(credentials)
        practice = preflight(api, gold, credentials)
        _write(f"signed in to {args.base_url}; loading {len(cases)} cases")
        waiting = Waiting(time.sleep, time.monotonic, args.poll_seconds, args.timeout_minutes * 60)
        outcomes = load_cases(LoadContext(api, gold, practice, waiting, render, _write), cases)
    finally:
        api.close()
    _write(*summary_lines(outcomes))
    return 0 if all_loaded(outcomes) else 1


def _write(*lines: str) -> None:
    sys.stdout.write("".join(f"{line}\n" for line in lines))
    sys.stdout.flush()


if __name__ == "__main__":
    raise SystemExit(main())
