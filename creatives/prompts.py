"""Prompt builders for offer / headline substitution."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class CreativeBrief:
    offer: str
    headline: str
    cta: str | None = None
    brand: str | None = None
    extra_instructions: str | None = None
    language: str = "ru"


def build_edit_prompt(brief: CreativeBrief, variant_index: int = 1) -> str:
    """Build a prompt that keeps reference style but swaps offer/headline."""
    lines = [
        "Create a new advertising creative in the same brand style as the attached reference image(s).",
        "Preserve layout structure, color palette, photography mood, iconography, and overall composition.",
        "Do not copy logos or trademarks from references unless they match the provided brand name.",
        "Replace promotional copy with the following:",
        f'- Headline: "{brief.headline}"',
        f'- Offer: "{brief.offer}"',
    ]
    if brief.cta:
        lines.append(f'- CTA button / label: "{brief.cta}"')
    if brief.brand:
        lines.append(f'- Brand name: "{brief.brand}"')

    lines.extend(
        [
            "Typography must be sharp and fully legible.",
            "Keep safe margins so text is not cropped after resizing to banner formats.",
            "Avoid watermarks, UI chrome, QR codes, and tiny unreadable text.",
            f"Produce variation #{variant_index}: keep the same brand system, "
            "but change composition emphasis, crop, or visual accent slightly.",
        ]
    )

    if brief.extra_instructions:
        lines.append(brief.extra_instructions.strip())

    if brief.language.lower().startswith("ru"):
        lines.append("All on-image text must be in Russian unless the brand name is Latin-only.")

    return "\n".join(lines)
