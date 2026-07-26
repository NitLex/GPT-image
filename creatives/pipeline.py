"""End-to-end creatives generation pipeline."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from openai import OpenAI

from .api import collect_reference_images, generate_from_references, save_bytes
from .prompts import CreativeBrief, build_edit_prompt
from .resize import export_all_sizes
from .sizes import BannerSize, parse_sizes

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PipelineConfig:
    references_dir: Path
    output_dir: Path
    offer: str
    headline: str
    cta: str | None = None
    brand: str | None = None
    extra_instructions: str | None = None
    variants: int = 3
    master_size: str = "1536x1024"
    quality: str = "high"
    model: str = "gpt-image-1.5"
    mode: str = "batch"  # batch | per_reference
    sizes: list[BannerSize] = field(default_factory=lambda: parse_sizes(None))
    resize_mode: str = "cover"
    fill_color: str = "#0B0B0B"
    output_format: str = "png"
    language: str = "ru"
    dry_run: bool = False


@dataclass(slots=True)
class PipelineResult:
    run_dir: Path
    masters: list[Path]
    resized: list[Path]


def _slug(text: str, max_len: int = 40) -> str:
    """ASCII slug for portable output folder names."""
    allowed = []
    for ch in text.lower().strip():
        if ("a" <= ch <= "z") or ("0" <= ch <= "9"):
            allowed.append(ch)
        elif ch in {" ", "-", "_"} or not ch.isascii():
            # Non-ASCII letters become separators to avoid mixed encodings in paths.
            allowed.append("-")
    slug = "".join(allowed).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return (slug or "creative")[:max_len]


def run_pipeline(client: OpenAI, config: PipelineConfig) -> PipelineResult:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_dir = config.output_dir / f"{timestamp}_{_slug(config.headline)}"
    masters_dir = run_dir / "masters"
    sizes_dir = run_dir / "sizes"
    masters_dir.mkdir(parents=True, exist_ok=True)
    sizes_dir.mkdir(parents=True, exist_ok=True)

    brief = CreativeBrief(
        offer=config.offer,
        headline=config.headline,
        cta=config.cta,
        brand=config.brand,
        extra_instructions=config.extra_instructions,
        language=config.language,
    )

    if config.dry_run:
        refs: list[Path] = []
        if config.references_dir.exists():
            try:
                refs = collect_reference_images(config.references_dir)
            except FileNotFoundError:
                refs = []
        logger.info(
            "Dry-run: %d reference(s) in %s",
            len(refs),
            config.references_dir,
        )
        logger.info("Output run directory: %s", run_dir)
        for i in range(1, config.variants + 1):
            prompt = build_edit_prompt(brief, variant_index=i)
            (run_dir / f"prompt_variant_{i:02d}.txt").write_text(prompt, encoding="utf-8")
        (run_dir / "references.txt").write_text(
            "\n".join(str(p) for p in refs) if refs else "(no references found)",
            encoding="utf-8",
        )
        logger.info("Dry-run complete. Prompts written to %s", run_dir)
        return PipelineResult(run_dir=run_dir, masters=[], resized=[])

    refs = collect_reference_images(config.references_dir)
    logger.info("Found %d reference(s) in %s", len(refs), config.references_dir)
    logger.info("Output run directory: %s", run_dir)

    masters: list[Path] = []
    resized: list[Path] = []

    jobs: list[tuple[str, list[Path]]]
    if config.mode == "per_reference":
        jobs = [(ref.stem, [ref]) for ref in refs]
    elif config.mode == "batch":
        jobs = [("batch", refs)]
    else:
        raise ValueError("mode must be 'batch' or 'per_reference'")

    for job_name, job_refs in jobs:
        for variant_idx in range(1, config.variants + 1):
            prompt = build_edit_prompt(brief, variant_index=variant_idx)
            prompt_path = run_dir / f"prompt_{job_name}_v{variant_idx:02d}.txt"
            prompt_path.write_text(prompt, encoding="utf-8")

            images = generate_from_references(
                client,
                reference_paths=job_refs,
                prompt=prompt,
                model=config.model,
                size=config.master_size,
                quality=config.quality,
                n=1,
            )
            master_path = masters_dir / f"{job_name}_v{variant_idx:02d}.png"
            save_bytes(images[0], master_path)
            masters.append(master_path)
            logger.info("Saved master: %s", master_path)

            exported = export_all_sizes(
                master_path,
                sizes_dir / f"{job_name}_v{variant_idx:02d}",
                config.sizes,
                resize_mode=config.resize_mode,
                fill_color=config.fill_color,
                output_format=config.output_format,
                stem=f"{job_name}_v{variant_idx:02d}",
            )
            resized.extend(exported)
            logger.info("Exported %d sizes for %s", len(exported), master_path.name)

    manifest = [
        f"offer: {config.offer}",
        f"headline: {config.headline}",
        f"cta: {config.cta or ''}",
        f"brand: {config.brand or ''}",
        f"model: {config.model}",
        f"master_size: {config.master_size}",
        f"variants: {config.variants}",
        f"mode: {config.mode}",
        f"masters: {len(masters)}",
        f"resized: {len(resized)}",
        "",
        "masters:",
        *[str(p.relative_to(run_dir)) for p in masters],
        "",
        "resized:",
        *[str(p.relative_to(run_dir)) for p in resized],
    ]
    (run_dir / "manifest.txt").write_text("\n".join(manifest) + "\n", encoding="utf-8")
    return PipelineResult(run_dir=run_dir, masters=masters, resized=resized)
