from pathlib import Path

from PIL import Image

from creatives.prompts import CreativeBrief, build_edit_prompt
from creatives.resize import export_all_sizes, resize_image
from creatives.sizes import BannerSize, parse_size


def test_parse_size():
    size = parse_size("300x250")
    assert size.width == 300
    assert size.height == 250


def test_prompt_contains_offer_and_headline():
    prompt = build_edit_prompt(
        CreativeBrief(offer="Скидка 30%", headline="Быстрая доставка", cta="Купить"),
        variant_index=2,
    )
    assert "Скидка 30%" in prompt
    assert "Быстрая доставка" in prompt
    assert "variation #2" in prompt


def test_resize_cover_exact_size(tmp_path: Path):
    master = Image.new("RGB", (1536, 1024), color=(20, 40, 80))
    master_path = tmp_path / "master.png"
    master.save(master_path)

    sizes = [BannerSize(300, 250), BannerSize(728, 90), BannerSize(970, 250)]
    exported = export_all_sizes(master_path, tmp_path / "out", sizes, resize_mode="cover")
    assert len(exported) == 3
    for path, size in zip(exported, sizes, strict=True):
        with Image.open(path) as img:
            assert img.size == (size.width, size.height)


def test_resize_contain_keeps_full_image():
    image = Image.new("RGB", (1000, 200), color=(255, 0, 0))
    result = resize_image(image, BannerSize(300, 250), mode="contain", fill_color="#000000")
    assert result.size == (300, 250)
