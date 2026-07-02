#!/usr/bin/env python3
"""Select Douyin author homepage target works from saved homepage JSON.

Input can be a single JSON file or a directory of JSON files. The script accepts
objects shaped like the Chrome/DOM probes used by this skill:

- {"authorName": "...", "allWorks": [{href,text,isPinned}, ...]}
- {"author": "...", "visibleWorks": [{href,text,isPinned}, ...]}
- {"authors": [{"author": "...", "allFirst": [...]}]}

It writes selected target rows plus shortage report rows. It never substitutes
another collection when the requested collection is too short.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


COLLECTIONS = {"homepage_all", "pinned", "non_pinned"}


def read_json_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    return sorted(p for p in path.glob("*.json") if p.is_file())


def is_pinned(work: dict[str, Any]) -> bool:
    if work.get("isPinned") is True or work.get("is_top") is True:
        return True
    text = str(work.get("text") or work.get("desc") or "")
    return text.strip().startswith("置顶") or "Tag: 置顶" in text


def normalize_work(work: dict[str, Any]) -> dict[str, Any]:
    href = work.get("href") or work.get("url") or work.get("post_url") or ""
    text = work.get("text") or work.get("desc") or work.get("title") or ""
    return {
        "href": href,
        "text": text,
        "isPinned": is_pinned(work),
        "raw": work,
    }


def extract_author_items(data: Any, fallback_name: str) -> list[dict[str, Any]]:
    if isinstance(data, dict) and isinstance(data.get("authors"), list):
        out = []
        for item in data["authors"]:
            works = item.get("allWorks") or item.get("allFirst") or item.get("visibleWorks") or []
            out.append({"author": item.get("author") or item.get("authorName") or fallback_name, "works": works})
        return out

    if isinstance(data, dict):
        works = data.get("allWorks") or data.get("allFirst") or data.get("visibleWorks") or []
        return [{"author": data.get("author") or data.get("authorName") or fallback_name, "works": works}]

    if isinstance(data, list):
        return [{"author": fallback_name, "works": data}]

    return []


def build_collection(works: list[dict[str, Any]], collection: str) -> list[dict[str, Any]]:
    normalized = [normalize_work(w) for w in works if isinstance(w, dict)]
    if collection == "homepage_all":
        return normalized
    if collection == "pinned":
        return [w for w in normalized if w["isPinned"]]
    if collection == "non_pinned":
        return [w for w in normalized if not w["isPinned"]]
    raise ValueError(f"unknown collection: {collection}")


def select_targets(
    input_path: Path,
    collection: str,
    start: int,
    end: int,
) -> dict[str, Any]:
    if collection not in COLLECTIONS:
        raise ValueError(f"--collection must be one of {sorted(COLLECTIONS)}")
    if start < 1 or end < start:
        raise ValueError("--start/--end are 1-based inclusive positions and must satisfy 1 <= start <= end")

    selected: list[dict[str, Any]] = []
    reports: list[dict[str, Any]] = []

    for file_path in read_json_files(input_path):
        data = json.loads(file_path.read_text(encoding="utf-8"))
        for item in extract_author_items(data, file_path.stem):
            author = item["author"]
            coll = build_collection(item["works"], collection)
            targets = coll[start - 1 : end]
            for offset, work in enumerate(targets, start=start):
                selected.append(
                    {
                        "author": author,
                        "target_collection": collection,
                        "target_position": offset,
                        "href": work["href"],
                        "text": work["text"],
                        "isPinned": work["isPinned"],
                    }
                )
            reports.append(
                {
                    "author": author,
                    "target_collection": collection,
                    "collection_count": len(coll),
                    "target_start": start,
                    "target_end": end,
                    "target_count": len(targets),
                    "status": "ok" if targets else "shortage",
                    "conclusion": (
                        "target slice available"
                        if targets
                        else f"{collection} collection has {len(coll)} item(s); positions {start}-{end} are unavailable"
                    ),
                }
            )

    return {
        "target_rule": {
            "collection": collection,
            "start": start,
            "end": end,
            "position_base": "1-based inclusive",
        },
        "selected": selected,
        "reports": reports,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="JSON file or directory of JSON files")
    parser.add_argument("--collection", required=True, choices=sorted(COLLECTIONS))
    parser.add_argument("--start", required=True, type=int, help="1-based inclusive start position")
    parser.add_argument("--end", required=True, type=int, help="1-based inclusive end position")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    result = select_targets(args.input, args.collection, args.start, args.end)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "selected": len(result["selected"]), "reports": len(result["reports"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
