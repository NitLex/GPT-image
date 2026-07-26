#!/usr/bin/env python3
"""Resize existing master creatives into banner sizes (no API calls)."""

from __future__ import annotations

import argparse
from pathlib import Path

from creatives.resize import export_all_sizes
from creatives.sizes import parse_sizes

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Resize master images to banner sizes")
    parser.add_argument("input", type=Path, help="Master image file or folder")
    parser.add_argument("--output", type=Path, default=Path("output/resized"))
    parser.add_argument(
        "--sizes",
        nargs="+",
        default=["300x250", "728x90", "970x250", "160x600", "300x600", "320x50"],
    )
    parser.add_argument("--resize-mode", choices=["cover", "contain"], default="cover")
    parser.add_argument("--fill-color", default="#0B0B0B")
    parser.add_argument("--format", dest="output_format", default="png")
    args = parser.parse_args()

    if args.input.is_dir():
        masters = sorted(
            p for p in args.input.iterdir() if p.suffix.lower() in IMAGE_EXTENSIONS
        )
    else:
        masters = [args.input]

    if not masters:
        raise SystemExit(f"No images found in {args.input}")

    sizes = parse_sizes(args.sizes)
    total = 0
    for master in masters:
        exported = export_all_sizes(
            master,
            args.output / master.stem,
            sizes,
            resize_mode=args.resize_mode,
            fill_color=args.fill_color,
            output_format=args.output_format,
            stem=master.stem,
        )
        total += len(exported)
        print(f"{master.name}: {len(exported)} sizes")

    print(f"Done. {total} files in {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
