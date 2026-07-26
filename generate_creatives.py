#!/usr/bin/env python3
"""CLI: generate ad creatives from references via GPT Image API, then resize."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv
from openai import OpenAI

from creatives.pipeline import PipelineConfig, run_pipeline
from creatives.sizes import parse_sizes


def _load_yaml_config(path: Path | None) -> dict:
    if path is None:
        return {}
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config must be a mapping: {path}")
    return data


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate multiple ad creatives from a references folder using the "
            "GPT Image API, substitute offer/headline, then resize to banner sizes."
        )
    )
    parser.add_argument("--config", type=Path, help="Optional YAML config file")
    parser.add_argument(
        "--references",
        type=Path,
        default=None,
        help="Folder with reference creatives (default: references/)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output directory (default: output/)",
    )
    parser.add_argument("--offer", help="Offer text to place on creatives")
    parser.add_argument("--headline", help="Headline / title text")
    parser.add_argument("--cta", help="Optional CTA label")
    parser.add_argument("--brand", help="Optional brand name")
    parser.add_argument(
        "--extra",
        dest="extra_instructions",
        help="Extra style / legal instructions for the model",
    )
    parser.add_argument(
        "--variants",
        type=int,
        default=None,
        help="Number of variants to generate (default: 3)",
    )
    parser.add_argument(
        "--sizes",
        nargs="+",
        help="Target sizes, e.g. 300x250 728x90 970x250",
    )
    parser.add_argument(
        "--master-size",
        default=None,
        help="API generation size, e.g. 1536x1024 or auto",
    )
    parser.add_argument(
        "--quality",
        choices=["low", "medium", "high", "auto"],
        default=None,
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Image model (default: gpt-image-1.5 or OPENAI_IMAGE_MODEL)",
    )
    parser.add_argument(
        "--mode",
        choices=["batch", "per_reference"],
        default=None,
        help="batch = all refs together; per_reference = one job per file",
    )
    parser.add_argument(
        "--resize-mode",
        choices=["cover", "contain"],
        default=None,
        help="How to fit masters into banner sizes",
    )
    parser.add_argument("--fill-color", default=None, help="Letterbox color for contain mode")
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=["png", "jpeg", "jpg", "webp"],
        default=None,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build prompts and folders without calling the API",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser


def resolve_config(args: argparse.Namespace) -> PipelineConfig:
    file_cfg = _load_yaml_config(args.config)

    def pick(cli_value, key, default=None):
        if cli_value is not None:
            return cli_value
        if key in file_cfg and file_cfg[key] is not None:
            return file_cfg[key]
        return default

    offer = pick(args.offer, "offer")
    headline = pick(args.headline, "headline")
    if not offer or not headline:
        raise SystemExit("Both --offer and --headline are required (CLI or config).")

    model = pick(args.model, "model", os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1.5"))
    sizes_raw = pick(args.sizes, "sizes")

    return PipelineConfig(
        references_dir=Path(pick(args.references, "references_dir", "references")),
        output_dir=Path(pick(args.output, "output_dir", "output")),
        offer=str(offer),
        headline=str(headline),
        cta=pick(args.cta, "cta"),
        brand=pick(args.brand, "brand"),
        extra_instructions=pick(args.extra_instructions, "extra_instructions"),
        variants=int(pick(args.variants, "variants", 3)),
        master_size=str(pick(args.master_size, "master_size", "1536x1024")),
        quality=str(pick(args.quality, "quality", "high")),
        model=str(model),
        mode=str(pick(args.mode, "mode", "batch")),
        sizes=parse_sizes(sizes_raw),
        resize_mode=str(pick(args.resize_mode, "resize_mode", "cover")),
        fill_color=str(pick(args.fill_color, "fill_color", "#0B0B0B")),
        output_format=str(pick(args.output_format, "output_format", "png")).replace(
            "jpg", "jpeg"
        ),
        dry_run=bool(args.dry_run),
    )


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    config = resolve_config(args)

    if config.dry_run:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "dry-run"))
    else:
        if not os.getenv("OPENAI_API_KEY"):
            raise SystemExit(
                "OPENAI_API_KEY is not set. Copy .env.example to .env and add your key."
            )
        client = OpenAI()

    result = run_pipeline(client, config)
    print(f"Done. Run folder: {result.run_dir}")
    print(f"Masters: {len(result.masters)}")
    print(f"Resized files: {len(result.resized)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
