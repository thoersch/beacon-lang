#!/usr/bin/env python3
from pathlib import Path
import argparse
import sys

ROOTS = (Path("compiler"), Path("std"), Path("examples"))


def beacon_files():
    files = []
    for root in ROOTS:
        if root.exists():
            files.extend(root.rglob("*.beacon"))
    return sorted(files)


def indent_width(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def next_nonblank(lines: list[str], start: int) -> int | None:
    for index in range(start, len(lines)):
        if lines[index].strip():
            return index
    return None


def violations(path: Path) -> list[tuple[int, int]]:
    lines = path.read_text().splitlines()
    found = []
    for index, line in enumerate(lines):
        if line.strip() != "else":
            continue
        child = next_nonblank(lines, index + 1)
        if child is None:
            continue
        child_text = lines[child].strip()
        if (
            indent_width(lines[child]) > indent_width(line)
            and child_text.startswith("if ")
            and child_text.endswith(" then")
        ):
            found.append((index + 1, child + 1))
    return found


def flatten_once(lines: list[str]) -> tuple[list[str], bool]:
    for outer_else in range(len(lines)):
        if lines[outer_else].strip() != "else":
            continue

        nested_if = next_nonblank(lines, outer_else + 1)
        if nested_if is None:
            continue

        base_indent = indent_width(lines[outer_else])
        nested_indent = indent_width(lines[nested_if])
        nested_text = lines[nested_if].strip()
        if (
            nested_indent <= base_indent
            or not nested_text.startswith("if ")
            or not nested_text.endswith(" then")
        ):
            continue

        nested_end = None
        for index in range(nested_if + 1, len(lines)):
            if indent_width(lines[index]) == nested_indent and lines[index].strip() == "end":
                nested_end = index
                break
        if nested_end is None:
            continue

        outer_end = next_nonblank(lines, nested_end + 1)
        if outer_end is None:
            continue
        if indent_width(lines[outer_end]) != base_indent:
            continue
        if lines[outer_end].strip() not in ("end", "end,"):
            continue

        newline = "\n" if lines[outer_else].endswith("\n") else ""
        header = " " * base_indent + "else " + nested_text
        dedent = nested_indent - base_indent
        body = []
        for line in lines[nested_if + 1:nested_end]:
            if line.strip() and line.startswith(" " * dedent):
                body.append(line[dedent:])
            else:
                body.append(line)

        result = lines[:outer_else] + [header] + body + lines[nested_end + 1:]
        return result, True

    return lines, False


def fix(path: Path) -> bool:
    original = path.read_text()
    trailing_newline = original.endswith("\n")
    lines = original.splitlines()
    changed = False

    while True:
        lines, flattened = flatten_once(lines)
        if not flattened:
            break
        changed = True

    if changed:
        updated = "\n".join(lines)
        if trailing_newline:
            updated += "\n"
        path.write_text(updated)
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Enforce Beacon's canonical flattened else-if style."
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Flatten safe else + sole nested-if chains before checking.",
    )
    args = parser.parse_args()

    files = beacon_files()
    if args.fix:
        for path in files:
            fix(path)

    failed = False
    for path in files:
        for else_line, if_line in violations(path):
            failed = True
            print(
                f"{path}:{else_line}: nested if on line {if_line} should use 'else if'",
                file=sys.stderr,
            )

    if failed:
        print(
            "Beacon style requires an if that directly follows else to use flattened 'else if' syntax.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
