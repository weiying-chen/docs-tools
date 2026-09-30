#!/usr/bin/env python3
"""Build a reference bundle from recent chus subtitle and SUPER source files."""

from __future__ import annotations

import argparse
import codecs
import re
import sys
from dataclasses import dataclass
from pathlib import Path


DEFAULT_ROOT = Path.home() / "text" / "docs"
DEFAULT_LATEST_BATCH_COUNT = 4
DOC_FOLDER_RE = re.compile(r"doc-(\d+)")


@dataclass(frozen=True)
class Batch:
    folder: Path
    number: int
    subtitle: Path
    super_file: Path


def source_txt_files(folder: Path) -> list[Path]:
    return sorted(
        path
        for path in folder.glob("*.txt")
        if not path.name.startswith("~")
        and not path.name.endswith(".baseline.txt")
    )


def has_final_outputs(folder: Path) -> bool:
    output = folder / "output"
    if not output.is_dir():
        return False
    names = [path.name.lower() for path in output.glob("*.docx") if path.is_file()]
    return any(name.endswith("_字幕_final.docx") for name in names) and any(
        name.endswith("_super_final.docx") for name in names
    )


def discover_batches(root: Path) -> list[Batch]:
    batches: list[Batch] = []
    for folder in root.iterdir():
        match = DOC_FOLDER_RE.fullmatch(folder.name)
        if not match or not folder.is_dir():
            continue
        files = source_txt_files(folder)
        subtitles = [path for path in files if "chus" in path.name.lower()]
        supers = [path for path in files if "super" in path.name.lower()]
        if len(subtitles) == 1 and len(supers) == 1 and has_final_outputs(folder):
            batches.append(
                Batch(folder, int(match.group(1)), subtitles[0], supers[0])
            )
    return sorted(batches, key=lambda batch: batch.number)


def latest_batches(batches: list[Batch], limit: int) -> list[Batch]:
    if limit < 1:
        raise ValueError("limit must be at least 1")
    return batches[-limit:]


def normalized_source(path: Path) -> str:
    data = path.read_bytes()
    encoding = (
        "utf-16"
        if data.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE))
        else "utf-8-sig"
    )
    return data.decode(encoding).replace("\r\n", "\n").replace("\r", "\n").strip()


def append_source(
    lines: list[str], root: Path, heading: str, path: Path
) -> None:
    lines.extend(
        [
            "",
            heading,
            "",
            f"Filename: `{path.relative_to(root).as_posix()}`",
            "",
            normalized_source(path),
        ]
    )


def render_bundle(root: Path, batches: list[Batch]) -> str:
    lines = [
        f"# Latest {len(batches)} Document References",
        "",
        "Recent complete `doc-N` folders, with each original `chus` subtitle "
        "source followed by its matching `super` source.",
    ]
    for batch in batches:
        lines.extend(["", "---", "", f"# {batch.folder.name}"])
        append_source(lines, root, "## CHUS subtitles", batch.subtitle)
        append_source(lines, root, "## SUPER", batch.super_file)
    return "\n".join(lines).rstrip() + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_ROOT,
        help=f"document project root (default: {DEFAULT_ROOT})",
    )
    parser.add_argument(
        "--latest",
        type=int,
        default=DEFAULT_LATEST_BATCH_COUNT,
        help=(
            "maximum number of latest complete folders to include "
            f"(default: {DEFAULT_LATEST_BATCH_COUNT})"
        ),
    )
    parser.add_argument(
        "--check", action="store_true", help="report a stale reference without rewriting it"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="show the target without rewriting it"
    )
    args = parser.parse_args(argv)
    if args.latest < 1:
        parser.error("--latest must be at least 1")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.root.expanduser().resolve()
    if not root.is_dir():
        print(f"[error] document root not found: {root}", file=sys.stderr)
        return 2

    batches = latest_batches(discover_batches(root), args.latest)
    if not batches:
        print("[error] no complete document folders found", file=sys.stderr)
        return 1

    output = root / "refs" / f"latest-{len(batches)}-docs.md"
    content = render_bundle(root, batches)
    changed = not output.exists() or output.read_text(encoding="utf-8") != content
    if args.check:
        if changed:
            print(f"stale: {output}", file=sys.stderr)
            return 1
        print("reference file is up to date")
        return 0
    if args.dry_run:
        print(f"would update: {output}" if changed else "reference file is up to date")
        return 0

    output.parent.mkdir(parents=True, exist_ok=True)
    if changed:
        output.write_text(content, encoding="utf-8")
        print(f"updated: {output}")
    else:
        print("reference file is up to date")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
