#!/usr/bin/env python3
"""Build a clean distributable zip for this Codex skill package."""

from __future__ import annotations

import argparse
import fnmatch
import os
import re
import zipfile
from pathlib import Path


DEFAULT_EXCLUDES = [
    ".git/**",
    ".git",
    ".env",
    "cookies.json",
    "runs/**",
    "downloads/**",
    "chrome-cdp-profile/**",
    "tests/**",
    "tools/**",
    "__pycache__/**",
    "**/__pycache__/**",
    "*.pyc",
    ".DS_Store",
    "dist/**",
]


def excluded(rel: str, patterns: list[str]) -> bool:
    rel = rel.replace(os.sep, "/")
    return any(fnmatch.fnmatch(rel, pat) for pat in patterns)


def read_skill_name(root: Path) -> str:
    skill_md = root / "SKILL.md"
    if not skill_md.exists():
        return root.name

    text = skill_md.read_text(encoding="utf-8")
    match = re.search(r"^---\s*\n(.*?)\n---\s*", text, flags=re.DOTALL)
    if not match:
        return root.name

    for line in match.group(1).splitlines():
        key, _, value = line.partition(":")
        if key.strip() == "name" and value.strip():
            return value.strip().strip("'\"")
    return root.name


def build_zip(root: Path, output: Path, excludes: list[str]) -> int:
    output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    prefix = read_skill_name(root)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            if excluded(rel, excludes):
                continue
            zf.write(path, f"{prefix}/{rel}")
            count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, default=Path("dist/douyin-author-homepage-collector.zip"))
    parser.add_argument("--exclude", action="append", default=[], help="Additional exclude glob, relative to root")
    args = parser.parse_args()

    output = args.output
    if not output.is_absolute():
        output = args.root / output
    count = build_zip(args.root.resolve(), output.resolve(), DEFAULT_EXCLUDES + args.exclude)
    print(f"created {output} with {count} files")


if __name__ == "__main__":
    main()
