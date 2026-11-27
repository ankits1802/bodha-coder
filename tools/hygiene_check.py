from __future__ import annotations

import argparse
import ast
import io
import json
import re
import subprocess
import sys
import tokenize
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "tools" / "hygiene_baseline.json"
TEXT_SUFFIXES = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".mjs",
    ".css",
    ".json",
    ".md",
    ".yml",
    ".yaml",
    ".toml",
    ".ini",
    ".sql",
    ".html",
    ".svg",
    ".mako",
    ".txt",
    ".example",
    ".sh",
    ".lock",
}
HASH_COMMENT_SUFFIXES = {".yml", ".yaml", ".toml", ".ini", ".example", ".sh", ".lock"}
HASH_COMMENT_NAMES = {".gitignore", ".dockerignore", "Dockerfile"}
SLASH_COMMENT_SUFFIXES = {".ts", ".tsx", ".js", ".mjs", ".css"}
PYTHON_DIRECTIVES = ("# noqa", "# type: ignore")
VENDORED = {
    "backend/app/codes/cms_mips_2026.py",
    "backend/app/codes/catalog_pfs.py",
    "backend/app/codes/mips_catalog.py",
    "backend/app/codes/mips_reporting_codes.py",
}
SLASH_TOKENS = re.compile(
    r"""(?P<string>"(?:\\.|[^"\\\n])*"|'(?:\\.|[^'\\\n])*'|`(?:\\.|[^`\\])*`)"""
    r"""|(?<![:\w])(?P<comment>//[^\n]*|/\*.*?\*/)""",
    re.S,
)
BUDGETS = {"python_file_lines": 400, "function_lines": 40, "positional_params": 5, "nesting": 3, "component_lines": 150}
LAYER_IMPORTS = {
    "main": {"api", "adapters", "codes", "core"},
    "worker": {"services", "adapters", "ai", "codes", "core", "models"},
    "scripts": {"core", "models"},
    "api": {"services", "adapters", "codes", "core", "models"},
    "services": {"ai", "adapters", "codes", "core", "models"},
    "adapters": {"ai", "core"},
    "ai": {"codes", "core"},
    "codes": set(),
    "core": {"models"},
    "models": set(),
}
NESTING_NODES = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith, ast.Try, ast.Match)


def tracked_files() -> list[Path]:
    listed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    paths = [
        ROOT / name for name in listed if Path(name).suffix in TEXT_SUFFIXES or Path(name).name in HASH_COMMENT_NAMES
    ]
    return [path for path in paths if path.is_file()]


def encoding_problems(raw: bytes) -> list[str]:
    problems = []
    if raw.startswith(b"\xef\xbb\xbf"):
        problems.append("byte-order mark")
    if b"\r\n" in raw:
        problems.append("CRLF line endings")
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError:
        problems.append("not UTF-8")
    return problems


def python_comments(text: str) -> int:
    comments = sum(
        1
        for token in tokenize.generate_tokens(io.StringIO(text).readline)
        if token.type == tokenize.COMMENT and not token.string.startswith(PYTHON_DIRECTIVES)
    )
    tree = ast.parse(text)
    holders = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
    return comments + sum(
        1 for node in ast.walk(tree) if isinstance(node, holders) and ast.get_docstring(node) is not None
    )


def slash_comments(text: str) -> int:
    return sum(1 for match in SLASH_TOKENS.finditer(text) if match.group("comment"))


def comment_count(path: Path, text: str) -> int:
    if path.suffix == ".py":
        return python_comments(text)
    if path.suffix in SLASH_COMMENT_SUFFIXES:
        return slash_comments(text)
    if path.suffix in HASH_COMMENT_SUFFIXES or path.name in HASH_COMMENT_NAMES:
        return sum(1 for line in text.splitlines() if line.lstrip().startswith("#"))
    if path.suffix in {".html", ".svg"}:
        return text.count("<!--")
    return 0


def nesting(node: ast.AST, depth: int = 0) -> int:
    deeper = depth + 1 if isinstance(node, NESTING_NODES) else depth
    return max([deeper, *(nesting(child, deeper) for child in ast.iter_child_nodes(node))])


def python_budgets(text: str) -> Counter[str]:
    counts: Counter[str] = Counter()
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            counts["functions_over_lines"] += (node.end_lineno or node.lineno) - node.lineno + 1 > BUDGETS[
                "function_lines"
            ]
            positional = [a for a in node.args.posonlyargs + node.args.args if a.arg not in ("self", "cls")]
            counts["functions_over_params"] += len(positional) > BUDGETS["positional_params"]
            counts["functions_over_nesting"] += nesting(node) > BUDGETS["nesting"]
    return counts


def layer_violations(path: Path, text: str) -> list[str]:
    parts = path.relative_to(ROOT).parts
    if parts[:2] != ("backend", "app") or len(parts) < 3:
        return []
    layer = Path(parts[2]).stem
    allowed = LAYER_IMPORTS.get(layer)
    if allowed is None:
        return (
            [f"{path.relative_to(ROOT)}: package '{layer}' has no row in LAYER_IMPORTS"]
            if parts[2] != "__init__.py"
            else []
        )
    imported = {
        node.module.split(".")[1]
        for node in ast.walk(ast.parse(text))
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("app.")
    }
    return [
        f"{path.relative_to(ROOT)}: {layer} may not import {target}" for target in sorted(imported - allowed - {layer})
    ]


def measure() -> tuple[Counter[str], list[str]]:
    counts: Counter[str] = Counter()
    failures: list[str] = []
    for path in tracked_files():
        relative = path.relative_to(ROOT).as_posix()
        raw = path.read_bytes()
        failures += [f"{relative}: {problem}" for problem in encoding_problems(raw)]
        text = raw.decode("utf-8", errors="replace")
        found = comment_count(path, text)
        if found:
            failures.append(f"{relative}: {found} comment(s)")
        if path.suffix == ".py" and relative not in VENDORED:
            counts["python_files_over_lines"] += text.count("\n") > BUDGETS["python_file_lines"]
            counts.update(python_budgets(text))
            failures += layer_violations(path, text)
        if path.suffix == ".tsx":
            counts["components_over_lines"] += text.count("\n") > BUDGETS["component_lines"]
    debt = ROOT / "docs" / "TECH_DEBT.md"
    counts["tech_debt_entries"] = debt.read_text(encoding="utf-8").count("\n### ") if debt.exists() else 0
    return counts, failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--update-baseline", action="store_true")
    args = parser.parse_args()
    counts, failures = measure()
    baseline = json.loads(BASELINE.read_text(encoding="utf-8")) if BASELINE.exists() else {}
    if args.update_baseline:
        BASELINE.write_text(json.dumps(dict(sorted(counts.items())), indent=2) + "\n", encoding="utf-8", newline="\n")
        return 0
    for key in sorted(set(counts) | set(baseline)):
        if counts.get(key, 0) > baseline.get(key, 0):
            failures.append(f"{key}: {counts.get(key, 0)} is above the baseline {baseline.get(key, 0)}")
        elif counts.get(key, 0) < baseline.get(key, 0) and key != "tech_debt_entries":
            failures.append(f"{key}: {counts.get(key, 0)} is below the baseline; run with --update-baseline")
    sys.stdout.write("\n".join(failures) + ("\n" if failures else "hygiene check passed\n"))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
