"""Standard display / IAB banner sizes and parsing helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BannerSize:
    width: int
    height: int
    name: str | None = None

    @property
    def label(self) -> str:
        base = f"{self.width}x{self.height}"
        return f"{self.name}_{base}" if self.name else base

    @property
    def aspect_ratio(self) -> float:
        return self.width / self.height

    def as_api_size(self) -> str:
        return f"{self.width}x{self.height}"


# Common IAB / Google Display Network sizes
DEFAULT_BANNER_SIZES: tuple[BannerSize, ...] = (
    BannerSize(300, 250, "medium_rectangle"),
    BannerSize(728, 90, "leaderboard"),
    BannerSize(970, 250, "billboard"),
    BannerSize(160, 600, "wide_skyscraper"),
    BannerSize(300, 600, "half_page"),
    BannerSize(320, 50, "mobile_banner"),
    BannerSize(336, 280, "large_rectangle"),
    BannerSize(970, 90, "large_leaderboard"),
    BannerSize(250, 250, "square"),
    BannerSize(1200, 628, "social_landscape"),
)


def parse_size(value: str | BannerSize) -> BannerSize:
    if isinstance(value, BannerSize):
        return value
    raw = value.strip().lower().replace("*", "x").replace("×", "x")
    if "x" not in raw:
        raise ValueError(f"Invalid size '{value}'. Expected WIDTHxHEIGHT, e.g. 300x250")
    width_s, height_s = raw.split("x", 1)
    return BannerSize(int(width_s), int(height_s))


def parse_sizes(values: list[str] | None) -> list[BannerSize]:
    if not values:
        return list(DEFAULT_BANNER_SIZES)
    return [parse_size(v) for v in values]


def nearest_master_size(target: BannerSize) -> str:
    """Pick an API-friendly master size closest to the target aspect ratio."""
    candidates = (
        ("1024x1024", 1.0),
        ("1536x1024", 1.5),
        ("1024x1536", 1024 / 1536),
    )
    ratio = target.aspect_ratio
    best = min(candidates, key=lambda item: abs(item[1] - ratio))
    return best[0]
