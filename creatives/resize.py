"""Local resizing of master creatives into banner sizes."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from .sizes import BannerSize


def _hex_to_rgb(color: str) -> tuple[int, int, int]:
    value = color.strip().lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    if len(value) != 6:
        raise ValueError(f"Invalid hex color: {color}")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def resize_cover(image: Image.Image, size: BannerSize) -> Image.Image:
    """Scale and center-crop so the image fully covers the target size."""
    src = image.convert("RGBA")
    src_ratio = src.width / src.height
    dst_ratio = size.aspect_ratio

    if src_ratio > dst_ratio:
        # Source is wider — match height, crop width.
        new_height = size.height
        new_width = max(1, round(new_height * src_ratio))
    else:
        # Source is taller — match width, crop height.
        new_width = size.width
        new_height = max(1, round(new_width / src_ratio))

    scaled = src.resize((new_width, new_height), Image.Resampling.LANCZOS)
    left = (scaled.width - size.width) // 2
    top = (scaled.height - size.height) // 2
    return scaled.crop((left, top, left + size.width, top + size.height))


def resize_contain(
    image: Image.Image,
    size: BannerSize,
    fill_color: str = "#0B0B0B",
) -> Image.Image:
    """Fit the full image inside the target size, padding with fill_color."""
    src = image.convert("RGBA")
    fitted = src.copy()
    fitted.thumbnail((size.width, size.height), Image.Resampling.LANCZOS)

    canvas = Image.new("RGBA", (size.width, size.height), (*_hex_to_rgb(fill_color), 255))
    offset = ((size.width - fitted.width) // 2, (size.height - fitted.height) // 2)
    canvas.paste(fitted, offset, fitted)
    return canvas


def resize_image(
    image: Image.Image,
    size: BannerSize,
    mode: str = "cover",
    fill_color: str = "#0B0B0B",
) -> Image.Image:
    mode_normalized = mode.strip().lower()
    if mode_normalized == "cover":
        return resize_cover(image, size)
    if mode_normalized == "contain":
        return resize_contain(image, size, fill_color=fill_color)
    raise ValueError("resize_mode must be 'cover' or 'contain'")


def save_image(image: Image.Image, path: Path, output_format: str = "png") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fmt = output_format.lower()
    if fmt == "jpg":
        fmt = "jpeg"

    to_save = image
    save_kwargs: dict = {}
    if fmt in {"jpeg", "jpg"}:
        to_save = image.convert("RGB")
        save_kwargs["quality"] = 92
        save_kwargs["optimize"] = True
    elif fmt == "webp":
        save_kwargs["quality"] = 90
        save_kwargs["method"] = 6
    elif fmt == "png":
        save_kwargs["optimize"] = True
    else:
        raise ValueError(f"Unsupported output format: {output_format}")

    path = path.with_suffix(f".{ 'jpg' if fmt == 'jpeg' else fmt}")
    to_save.save(path, format=fmt.upper() if fmt != "jpeg" else "JPEG", **save_kwargs)
    return path


def export_all_sizes(
    master_path: Path,
    output_dir: Path,
    sizes: list[BannerSize],
    *,
    resize_mode: str = "cover",
    fill_color: str = "#0B0B0B",
    output_format: str = "png",
    stem: str | None = None,
) -> list[Path]:
    with Image.open(master_path) as img:
        base = img.copy()

    name_stem = stem or master_path.stem
    exported: list[Path] = []
    for size in sizes:
        resized = resize_image(base, size, mode=resize_mode, fill_color=fill_color)
        out_path = output_dir / f"{name_stem}_{size.label}.{output_format}"
        exported.append(save_image(resized, out_path, output_format=output_format))
    return exported
