#!/usr/bin/env python3
from pathlib import Path
import sys

ROOTS = (Path("compiler"), Path("std"), Path("examples"))


def beacon_files():
    files = []
    for root in ROOTS:
        if root.exists():
            files.extend(root.rglob("*.beacon"))
    return sorted(files)


def indent_width(line: str) -> int:
    return len(line) - len(line.lstrip(" \t"))


def next_significant(lines: list[str], start: int) -> int | None:
    for index in range(start, len(lines)):
        stripped = lines[index].strip()
        if stripped and not stripped.startswith("//"):
            return index
    return None


def violations(path: Path) -> list[tuple[int, int]]:
    lines = path.read_text().splitlines()
    found = []

    for index, line in enumerate(lines):
        if line.strip() != "else":
            continue

        child = next_significant(lines, index + 1)
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


def main() -> int:
    failed = False

    for path in beacon_files():
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
