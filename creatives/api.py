"""Thin wrapper around OpenAI GPT Image API."""

from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import BinaryIO, Iterable

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


def collect_reference_images(folder: Path) -> list[Path]:
    if not folder.exists() or not folder.is_dir():
        raise FileNotFoundError(f"References folder not found: {folder}")
    files = sorted(
        p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    )
    if not files:
        raise FileNotFoundError(
            f"No reference images found in {folder}. "
            f"Supported: {', '.join(sorted(IMAGE_EXTENSIONS))}"
        )
    return files


def _open_images(paths: Iterable[Path]) -> list[tuple[str, BinaryIO]]:
    opened: list[tuple[str, BinaryIO]] = []
    for path in paths:
        # Keep file handles open until the request finishes.
        opened.append((path.name, path.open("rb")))
    return opened


@retry(wait=wait_exponential_jitter(initial=2, max=30), stop=stop_after_attempt(4), reraise=True)
def generate_from_references(
    client: OpenAI,
    *,
    reference_paths: list[Path],
    prompt: str,
    model: str,
    size: str,
    quality: str,
    n: int = 1,
    input_fidelity: str | None = "high",
) -> list[bytes]:
    """Call /v1/images/edits with one or more reference images."""
    if n < 1:
        raise ValueError("n must be >= 1")

    handles = _open_images(reference_paths)
    try:
        image_payload = [handle for _, handle in handles]
        kwargs: dict = {
            "model": model,
            "image": image_payload if len(image_payload) > 1 else image_payload[0],
            "prompt": prompt,
            "size": size,
            "quality": quality,
            "n": n,
        }
        # gpt-image-2 rejects/ignores input_fidelity; older GPT Image models accept it.
        if input_fidelity and not model.startswith("gpt-image-2"):
            kwargs["input_fidelity"] = input_fidelity

        logger.info(
            "Requesting %s image(s) via %s (size=%s, quality=%s, refs=%d)",
            n,
            model,
            size,
            quality,
            len(reference_paths),
        )
        result = client.images.edit(**kwargs)
    finally:
        for _, handle in handles:
            handle.close()

    images: list[bytes] = []
    for item in result.data:
        if not item.b64_json:
            raise RuntimeError("API returned no b64_json image payload")
        images.append(base64.b64decode(item.b64_json))
    return images


def save_bytes(data: bytes, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path
