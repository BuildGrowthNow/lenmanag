from app.core.asset_utils import get_best_asset_url
from app.core.color_system import build_brand_palette, deduplicate_colors


def test_asset_fallback_uses_asset_value_not_page_url() -> None:
    cue = {
        "assetType": "logo",
        "value": "https://cdn.example.test/brand/logo.svg",
        "sourceUrl": "https://example.test/about",
        "cachedUri": None,
    }
    assert get_best_asset_url(cue) == "https://cdn.example.test/brand/logo.svg"


def test_asset_fallback_prefers_cached_url() -> None:
    cue = {
        "assetType": "logo",
        "assetUrl": "https://cdn.example.test/brand/logo.svg",
        "pageUrl": "https://example.test",
        "cachedUrl": "https://assets.example.test/logo.svg",
    }
    assert get_best_asset_url(cue) == "https://assets.example.test/logo.svg"


def test_palette_deduplicates_and_assigns_distinct_roles() -> None:
    assert deduplicate_colors(["#fff", "#ffffff", "#112233"]) == ["#ffffff", "#112233"]
    palette = build_brand_palette(["#fff", "#ffffff"])
    assert palette["primary"] != palette["secondary"]
    assert palette["primary"] == "#ffffff"

